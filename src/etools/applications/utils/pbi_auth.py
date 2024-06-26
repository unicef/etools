from django.conf import settings
from django.core.cache import cache

import msal
import requests


class TokenRetrieveException(BaseException):
    """Exception thrown when migration is failing due validation"""


pbi_config = settings.PBI_CONFIG


def get_access_token():
    # try to get it from cache:
    cache_key = 'lmsm_pbi_access_token'
    access_token = cache.get(cache_key, None)
    if not access_token:
        # cache.add(cache_key, access_token, timeout=1800)

        required_keys = ['AUTHENTICATION_MODE', 'WORKSPACE_ID',
                         'REPORT_ID', 'TENANT_ID',
                         'CLIENT_ID', 'CLIENT_SECRET', 'SCOPE_BASE', 'AUTHORITY_URL']

        if not all(key in pbi_config and pbi_config[key] for key in required_keys):
            raise TokenRetrieveException('Token required keys: {}'.format(required_keys))
        try:

            # Service Principal auth is the recommended by Microsoft to achieve App Owns Data Power BI embedding
            if pbi_config['AUTHENTICATION_MODE'].lower() == 'serviceprincipal':
                authority = pbi_config['AUTHORITY_URL'].replace('organizations', pbi_config['TENANT_ID'])
                clientapp = msal.ConfidentialClientApplication(pbi_config['CLIENT_ID'],
                                                               client_credential=pbi_config['CLIENT_SECRET'],
                                                               authority=authority)

                # Make a client call if Access token is not available in cache
                response = clientapp.acquire_token_for_client(scopes=pbi_config['SCOPE_BASE'])
            else:
                raise TokenRetrieveException(f"Not supported authentication mode: {pbi_config['AUTHENTICATION_MODE']}")

            try:
                token_return = response['access_token']
            except KeyError:
                raise TokenRetrieveException(response['error_description'])
            else:
                cache.add(cache_key, token_return, timeout=1800)
                return token_return
        except Exception as ex:
            raise TokenRetrieveException('Error retrieving Access token\n' + str(ex))

    return access_token


def get_embed_url(pbi_headers):
    workspace_id = pbi_config['WORKSPACE_ID']
    report_id = pbi_config['REPORT_ID']

    url_to_call = f'https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}'
    api_response = requests.get(url_to_call, headers=pbi_headers)
    if api_response.status_code == 200:
        r = api_response.json()
        return r["embedUrl"], r["datasetId"]
    else:
        raise TokenRetrieveException('Error retrieving Embed URL')


def get_embed_token(dataset_id, pbi_headers):
    workspace_id = pbi_config['WORKSPACE_ID']
    report_id = pbi_config['REPORT_ID']

    embed_token_api = 'https://api.powerbi.com/v1.0/myorg/GenerateToken'
    request_body = {
        "datasets": [{'id': dataset_id}],
        "reports": [{'id': report_id}],
        "targetWorkspaces": [{'id': workspace_id}]
    }
    api_response = requests.post(embed_token_api, json=request_body, headers=pbi_headers)
    if api_response.status_code == 200:
        return api_response.json()["token"]
    else:
        raise TokenRetrieveException('Error retrieving Embed Token')
