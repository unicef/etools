name = 'last_mile/wastage_transfer'
defaults = {
    'description': 'LMSM app: New items checked out as wastage by {{ transfer.partner_organization.name }}',
    'subject':  'LMSM app: New items checked out as wastage by {{ transfer.partner_organization.name }}',
    'html_content': """
        {% extends "email-templates/base" %}
        {% block content %}
        <h3>Wastage information</h3>
        <table border="1">
          <tr>
            <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                      box-sizing:border-box;max-height:56px;margin:0;
                                      padding:10px;overflow:hidden;
                                      background-color:#0099FF;">
                <span style="color: white;font-weight: bold;">IP Number</span>
            </td>
            <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                      box-sizing:border-box;max-height:56px;margin:0;
                                      padding:10px;overflow:hidden;
                                      background-color:#0099FF;">
                <span style="color: white;font-weight: bold;">Wastage ID</span>
            </td>
            <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                      box-sizing:border-box;width:100%;max-height:56px;margin:0;
                                      padding:10px;overflow:hidden;
                                      background-color:#0099FF;">
                <span style="color: white;font-weight: bold;">Checked In Date</span>
            </td>
            <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                      box-sizing:border-box;width:100%;max-height:56px;margin:0;
                                      padding:10px;overflow:hidden;
                                      background-color:#0099FF;">
                <span style="color: white;font-weight: bold;">Checked In By</span>
            </td>
            <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                      box-sizing:border-box;width:100%;max-height:56px;margin:0;
                                      padding:10px;overflow:hidden;
                                      background-color:#0099FF;">
                <span style="color: white;font-weight: bold;">Checked Out Date</span>
            </td>
            <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                      box-sizing:border-box;width:100%;max-height:56px;margin:0;
                                      padding:10px;overflow:hidden;
                                      background-color:#0099FF;">
                <span style="color: white;font-weight: bold;">Checked Out By</span>
            </td>
              <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                      box-sizing:border-box;width:100%;max-height:56px;margin:0;
                                      padding:10px;overflow:hidden;
                                      background-color:#0099FF;">
                <span style="color: white;font-weight: bold;">Location Name</span>
            </td>
            <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                      box-sizing:border-box;width:100%;max-height:56px;margin:0;
                                      padding:10px;overflow:hidden;
                                      background-color:#0099FF;">
                <span style="color: white;font-weight: bold;">Location Region</span>
            </td>
            <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                      box-sizing:border-box;width:100%;max-height:56px;margin:0;
                                      padding:10px;overflow:hidden;
                                      background-color:#0099FF;">
                <span style="color: white;font-weight: bold;">Location Type</span>
            </td>
            <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                      box-sizing:border-box;width:100%;max-height:56px;margin:0;
                                      padding:10px;overflow:hidden;
                                      background-color:#0099FF;">
                <span style="color: white;font-weight: bold;">Transfer Created</span>
            </td>
          </tr>
          <tr >
             <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                       box-sizing:border-box;padding:10px;">
                 {{ transfer.partner_organization.vendor_number }}
             </td>
             <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                       box-sizing:border-box;padding:10px;">
                 {{ transfer.partner_organization.id }}
             </td>
             <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                       box-sizing:border-box;padding:10px;">
                 {{ transfer.destination_check_in_at|date:'Y-m-d H:i' }}
             </td>
             <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                       box-sizing:border-box;padding:10px;">
                 {{ transfer.checked_in_by.full_name }}
             </td>
             <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                       box-sizing:border-box;padding:10px;">
                 {{ transfer.origin_check_out_at|date:'Y-m-d H:i' }}
             </td>
             <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                       box-sizing:border-box;padding:10px;">
                 {{ transfer.checked_out_by.full_name }}
             </td>
             <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                       box-sizing:border-box;padding:10px;">
                 {{ transfer.destination_point.name }}
             </td>
             <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                       box-sizing:border-box;padding:10px;">
                 {{ transfer.destination_point.parent }}
             </td>
             <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                       box-sizing:border-box;padding:10px;">
                 {{ transfer.destination_point.poi_type.name }}
             </td>
             <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                       box-sizing:border-box;padding:10px;">
                 {{ transfer.created|date:'Y-m-d H:i' }}
             </td>
          </tr>
      </table><br/>

        <h3>Items checked out as wastage</h3>
        <table border="1">
          <tr>
            <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                      box-sizing:border-box;max-height:56px;margin:0;
                                      padding:10px;overflow:hidden;
                                      background-color:#0099FF;border-radius:3px 3px 0 0;">
                <span style="color: white;font-weight: bold;">Material Number</span>
            </td>
            <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                      box-sizing:border-box;width:100%;max-height:56px;margin:0;
                                      padding:16px 20px 12px;overflow:hidden;
                                      background-color:#0099FF;border-radius:3px 3px 0 0;">
                <span style="color: white;font-weight: bold;">Material Description</span>
            </td>
            <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                      box-sizing:border-box;max-height:56px;margin:0;
                                      padding:16px 20px 12px;overflow:hidden;
                                      background-color:#0099FF;border-radius:3px 3px 0 0;">
                <span style="color: white;font-weight: bold;">Quantity</span>
            </td>
            <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                      box-sizing:border-box;max-height:56px;margin:0;
                                      padding:16px 20px 12px;overflow:hidden;
                                      background-color:#0099FF;border-radius:3px 3px 0 0;">
                <span style="color: white;font-weight: bold;">Unit</span>
            </td>
            <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                      box-sizing:border-box;width:100%;max-height:56px;margin:0;
                                      padding:16px 20px 12px;overflow:hidden;
                                      background-color:#0099FF;border-radius:3px 3px 0 0;">
                <span style="color: white;font-weight: bold;">Batch Id</span>
            </td>
            <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                      box-sizing:border-box;width:100%;max-height:56px;margin:0;
                                      padding:16px 20px 12px;overflow:hidden;
                                      background-color:#0099FF;border-radius:3px 3px 0 0;">
                <span style="color: white;font-weight: bold;">Expiry Date</span>
            </td>
            <td class="header" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                                      box-sizing:border-box;width:100%;max-height:56px;margin:0;
                                      padding:16px 20px 12px;overflow:hidden;
                                      background-color:#0099FF;border-radius:3px 3px 0 0;">
                <span style="color: red;font-weight: bold;">Shipment discrepancies</span>
            </td>
          </tr>
          {% for item in transfer.items.all %}
              </tr>
              <tr >
                 <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                           box-sizing:border-box;padding:10px;">
                     {{ item.material.number }}
                 </td>
                 <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                           box-sizing:border-box;padding:10px;">
                     {% if item.description %}{{ item.description }}{% else %}{{ item.material.short_description }}{% endif %}
                 </td>
                 <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                           box-sizing:border-box;padding:10px;">
                     {{ item.quantity }}
                 </td>
                 <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                           box-sizing:border-box;padding:10px;">
                     {% if item.unit %}{{ item.uom }}{% else %}{{ item.material.original_uom }}{% endif %}
                 </td>
                 <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                           box-sizing:border-box;padding:10px;">
                     {{ item.batch_id }}
                 </td>
                 <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                           box-sizing:border-box;padding:10px;">
                     {{ item.expiry_date|date:'Y-m-d H:i' }}
                 </td>
                 <td class="wrapper" style="font-family:sans-serif;font-size:14px;vertical-align:top;
                           box-sizing:border-box;padding:10px;">
                     {{ item.get_wastage_type_display }}
                 </td>
              </tr>
          {% endfor %}
      </table>
    <br/><br/>      
    Please note that this is an automatically generated message and replies to this email address are not monitored.
          
    {% endblock %}
        
        """
}
