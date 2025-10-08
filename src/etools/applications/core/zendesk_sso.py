import hashlib
import logging
import time
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.views.decorators.http import require_http_methods

import jwt

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def zendesk_sso_redirect(request):
    try:
        user = request.user

        zendesk_subdomain = getattr(settings, 'ZENDESK_SUBDOMAIN', None)
        shared_secret = getattr(settings, 'ZENDESK_SHARED_SECRET', None)

        if not zendesk_subdomain or not shared_secret:
            logger.error("Zendesk SSO configuration missing")
            return JsonResponse({
                'error': 'Zendesk SSO is not properly configured'
            }, status=500)

        return_to = request.GET.get('return_to', '')
        request_from_app = request.GET.get('request_from_app', '')

        iat = int(time.time())
        payload = {
            'jti': hashlib.md5(f"{user.email}{iat}".encode()).hexdigest(),
            'iat': iat,
            'email': user.email.lower(),
            'name': user.get_full_name() or user.username,
            'external_id': str(user.pk),
            'update': True,
        }

        tags = []
        if hasattr(user, 'profile'):
            if user.profile.organization:
                tags.append(f"org_{user.profile.organization.name.replace(' ', '_').lower()}")
                payload['organization'] = user.profile.organization.name
            if user.profile.country:
                tags.append(f"country_{user.profile.country.name.replace(' ', '_').lower()}")
                payload['user_fields'] = {
                    'country': user.profile.country.name,
                    'workspace': user.profile.country.name
                }

        tags.append('end_user')
        payload['role'] = 'end-user'
        if request_from_app:
            tags.append(request_from_app)

        if tags:
            payload['tags'] = tags

        token = jwt.encode(payload, shared_secret, algorithm='HS256')

        zendesk_sso_url = f"https://{zendesk_subdomain}.zendesk.com/access/jwt"

        params = {'jwt': token}
        if return_to:
            params['return_to'] = return_to

        redirect_url = f"{zendesk_sso_url}?{urlencode(params)}"
        return HttpResponseRedirect(redirect_url)

    except Exception as e:
        logger.exception(f"Error during Zendesk SSO: {str(e)}")
        return JsonResponse({
            'error': 'An error occurred during SSO authentication'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def zendesk_sso_info(request):
    try:
        zendesk_subdomain = getattr(settings, 'ZENDESK_SUBDOMAIN', None)
        shared_secret = getattr(settings, 'ZENDESK_SHARED_SECRET', None)
        is_configured = bool(zendesk_subdomain and shared_secret)
        response_data = {
            'sso_enabled': is_configured,
            'user': {
                'email': request.user.email,
                'name': request.user.get_full_name() or request.user.username,
            }
        }
        if is_configured:
            response_data['zendesk_subdomain'] = zendesk_subdomain
            response_data['knowledge_base_url'] = (
                f"https://{zendesk_subdomain}.zendesk.com/hc/en-us/categories/"
                "31285460572180-Last-Mile-Supply-Monitoring-Module"
            )

        return JsonResponse(response_data)

    except Exception as e:
        logger.exception(f"Error getting Zendesk SSO info: {str(e)}")
        return JsonResponse({
            'error': 'An error occurred while fetching SSO information'
        }, status=500)
