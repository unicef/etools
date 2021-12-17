name = 'base'
defaults = {
    'description': 'Base template for emails.',
    'html_content': """
                {% load static %}
                <!DOCTYPE html>
                <html>
                  <head>
                    <meta name="viewport" content="width=device-width">
                    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
                    <title>{% block title %}{% endblock %}</title>
                    <style type="text/css">
                      /* -------------------------------------
                          RESPONSIVE AND MOBILE FRIENDLY STYLES
                      ------------------------------------- */
                      @media only screen and (max-width: 620px) {
                        table[class=body] p,
                        table[class=body] ul,
                        table[class=body] ol,
                        table[class=body] td,
                        table[class=body] span,
                        table[class=body] a {}
                        table[class=body] .wrapper,
                        table[class=body] .article {
                          padding: 16px !important; }
                        table[class=body] .content {
                          padding: 10px !important; }
                        table[class=body] .container {
                          padding: 0 !important;
                          width: 100% !important; }
                        table[class=body] .main {
                          border-left-width: 0 !important;
                          border-radius: 0 !important;
                          border-right-width: 0 !important; }
                        table[class=body] .header,
                        table[class=body] .footer {
                          padding-left: 16px !important;
                          padding-right: 16px !important; }
                        table[class=body] .footer td {
                          vertical-align: bottom !important; }
                        table[class=body] .footer .links .br {
                          display: inline !important; }
                        table[class=body] .img-responsive {
                          height: auto !important;
                          max-width: 100% !important;
                          width: auto !important; }
                      }
                      @media only screen and (max-width: 480px) {
                        table[class=data-table] {
                          margin: 0 !important;
                          background-color: #F2F2F2;
                        }
                        table[class=data-table] .dt,
                        table[class=data-table] .df {
                          display: block !important;
                          width: 100% !important; }
                        table[class=data-table] .dt {
                          font-size: 12px !important;
                          padding: 8px 8px 4px !important;
                          background-color: transparent !important;
                          border-bottom: 0 !important; }
                        table[class=data-table] .df {
                          font-size: 14px !important;
                          padding: 0 8px 6px !important; }
                      }
                      @media only screen and (max-width: 320px) {
                        table[class=body] h1 {
                          font-size: 18px !important; }
                        table[class=body] .btn table {
                          width: 100% !important; }
                        table[class=body] .btn a {
                          width: 100% !important; }
                        table[class=data-table] .dt {
                          font-size: 11px !important; }
                        table[class=data-table] .df {
                          font-size: 13px !important; }
                      }
                      /* -------------------------------------
                          PRESERVE THESE STYLES IN THE HEAD
                      ------------------------------------- */
                      @media all {
                        .ExternalClass {
                          width: 100%; }
                        .ExternalClass,
                        .ExternalClass p,
                        .ExternalClass span,
                        .ExternalClass font,
                        .ExternalClass td,
                        .ExternalClass div {
                          line-height: 100%; }
                        .apple-link a {
                          color: inherit !important;
                          font-family: inherit !important;
                          font-size: inherit !important;
                          font-weight: inherit !important;
                          line-height: inherit !important;
                          text-decoration: none !important; }
                        .btn-primary table td:hover {
                          background-color: #0099FF !important; }
                        .btn-primary a:hover {
                          background-color: #0099FF !important;
                          border-color: #0099FF !important; }
                      }
                    </style>
                  </head>
                  <body style="background-color:#EEEEEE;font-family:sans-serif;-webkit-font-smoothing:antialiased;
                               font-size:14px;line-height:1.4;margin:0;padding:0;-ms-text-size-adjust:100%;
                               -webkit-text-size-adjust:100%;">
                    <table border="0" cellpadding="0" cellspacing="0" class="body"
                           style="border-collapse:separate;mso-table-lspace:0pt;mso-table-rspace:0pt;
                           background-color:#EEEEEE;width:100%;">
                      <tr>
                        <td style="font-family:sans-serif;font-size:14px;vertical-align:top;">&nbsp;</td>
                        <td class="container" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                                     display:block;max-width:580px;padding:10px;width:580px;
                                                     margin:0 auto !important;width:auto !important;">
                          <!-- START CENTERED WHITE CONTAINER -->
                          <div class="content" style="box-sizing:border-box;display:block;margin:0 auto;
                                                      max-width:580px;padding:10px 0;">
                            <!-- START MAIN CONTENT AREA -->
                            <table border="0" cellpadding="0" cellspacing="0" class="main"
                                   style="border-collapse:separate;mso-table-lspace:0pt;mso-table-rspace:0pt;
                                   background:#FFFFFF;border-radius:3px;width:100%;
                                   box-shadow:0 0 2px rgba(0,0,0,.12), 0 2px 2px rgba(0,0,0,.24);">
                              <!-- START HEADER -->
                              <tr>
                                <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                                          box-sizing:border-box;width:100%;max-height:56px;margin:0;
                                                          padding:16px 20px 12px;overflow:hidden;
                                                          background-color:#233944;border-radius:3px 3px 0 0;">
                                  <table border="0" cellpadding="0" cellspacing="0"
                                         style="border-collapse:separate;mso-table-lspace:0pt;
                                         mso-table-rspace:0pt;width:100%;">
                                    <tr>
                                      <td style="font-family:sans-serif;font-size:14px;vertical-align:top;">
                                        <!-- TODO: update image link with global -->
                                        <a href="https://etools.unicef.org" target="_blank"
                                           style="color:#0099FF;text-decoration:none;">
                                          <span style="color: white;text-decoration: none;">eTools</span>
                                        </a>
                                      </td>
                                    </tr>
                                  </table>
                                </td>
                              </tr>
                              <!-- END HEADER -->
                              <!-- START CONTENT -->
                              <tr>
                                <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                                           box-sizing:border-box;padding:20px;">
                                  <table border="0" cellpadding="0" cellspacing="0"
                                         style="border-collapse:separate;mso-table-lspace:0pt;
                                         mso-table-rspace:0pt;width:100%;">
                                    <tr>
                                      <td style="font-family:sans-serif;font-size:14px;vertical-align:top;">
                                          {% block content %}
                                          {% endblock %}
                                      </td>
                                    </tr>
                                  </table>
                                </td>
                              </tr>
                              <!-- END CONTENT -->
                              <tr>
                                <td class="footer"
                                    style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                    box-sizing:border-box;width:100%;max-height:56px;padding:14px 20px 14px;
                                    overflow:hidden;background-color:#E5F4FF;border-radius:0 0 3px 3px;">
                                  <table border="0" cellpadding="0" cellspacing="0"
                                         style="border-collapse:separate;mso-table-lspace:0pt;
                                         mso-table-rspace:0pt;width:100%;">
                                    <tr>
                                      <td style="font-family:sans-serif;font-size:14px;vertical-align:top;">
                                        <!-- TODO: update image link with global -->
                                        <a href="https://unicef.org" target="_blank"
                                           style="color:#0099FF;text-decoration:underline;">

                                           <img src='https://etools.unicef.org/pmp/images/UNICEF_logo.png'
                                                alt="Unicef" class="logo-unicef" width="101" height="24"
                                                style="border:none;-ms-interpolation-mode:bicubic;max-width:100%;
                                                       display:block;margin:0;padding:0;width:101px;height:24px;"/>
                                       </a>
                                      </td>
                                      <td class="links" style="font-family:sans-serif;font-size:14px;
                                                               vertical-align:top;text-align:right;">
                                        <!-- TODO: add links -->
                                        <!--
                                        <a href="#" target="_blank"
                                           style="color:#0099FF;text-decoration:underline;display:inline-block;
                                           margin:0;padding:4px;margin-left:10px;font-size:12px;text-decoration:none;">
                                            Contact
                                        </a>
                                        <span class="br" style="display:none;"><br/></span>

                                        <a href="#" target="_blank"
                                           style="color:#0099FF;text-decoration:underline;display:inline-block;
                                           margin:0;padding:4px;margin-left:10px;font-size:12px;text-decoration:none;">
                                            Disclaimer
                                        </a>
                                        <span class="br" style="display:none;"><br/></span>

                                        <a href="#" target="_blank"
                                           style="color:#0099FF;text-decoration:underline;display:inline-block;
                                           margin:0;padding:4px;margin-left:10px;font-size:12px;text-decoration:none;">
                                            Privacy Policy
                                        </a>
                                        <span class="br" style="display:none;"><br/></span>
                                        -->
                                      </td>
                                    </tr>
                                  </table>
                                </td>
                              </tr>
                              <!-- START FOOTER -->
                              <!-- END FOOTER -->
                            </table>
                            <!-- END MAIN CONTENT AREA -->
                          </div>
                          <!-- END CENTERED WHITE CONTAINER -->
                        </td>
                        <td style="font-family:sans-serif;font-size:14px;vertical-align:top;">&nbsp;</td>
                      </tr>
                    </table>
                  </body>
                </html>
                """
}
