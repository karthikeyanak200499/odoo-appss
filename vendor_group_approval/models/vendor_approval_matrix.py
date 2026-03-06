from odoo import models, fields


class VendorApprovalMatrix(models.Model):
    _name = "vendor.approval.matrix"
    _description = "Vendor Approval Matrix"
    _order = "create_date desc, id desc"

    res_partner_id = fields.Many2one(
        "res.partner",
        string="Vendor",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=False,
        default=lambda self: self.env.company,
        index=True,
    )
    approval_level_id = fields.Many2one(
        "vendor.approval.level",
        string="Approval Level",
        required=True,
    )
    level = fields.Integer(string="Sequence Level")
    approver_user_id = fields.Many2one(
        "res.users",
        string="Approver User",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Action By",
        required=True,
    )
    action = fields.Selection(
        [
            ("requested", "Requested"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Action",
        required=True,
    )
    approved_by = fields.Many2one("res.users", string="Approved By", copy=False)
    approved_on = fields.Datetime(string="Approved On", copy=False)
    approved_signature_html = fields.Html(string="Approved Signature", copy=False)
    notes = fields.Text(string="Notes")
