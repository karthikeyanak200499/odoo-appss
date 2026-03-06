{
    "name": "Vendor Group Approvals",
    "version": "17.0.1.0.0",
    "summary": "Vendor approval workflow with separate approval group and approval levels",
    "category": "Purchases",
    'author': "Karthikeyan A",
    "license": "LGPL-3",
    "depends": ["base", "mail", "purchase", "contacts"],
    "data": [
        "security/vendor_approval_security.xml",
        "security/ir.model.access.csv",
        "data/mail_templates.xml",
        "views/vendor_approval_group_views.xml",
        "views/res_partner_views.xml"
    ],
    "images": ['static/description/vendor_approval_group.png'],
    "installable": True,
    "application": False
}
