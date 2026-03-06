from odoo import models, fields


class VendorApprovalLevel(models.Model):
    _name = "vendor.approval.level"
    _description = "Vendor Approval Level"
    _order = "sequence, id"

    group_id = fields.Many2one(
        "vendor.approval.group",
        string="Approval Group",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="group_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    name = fields.Char(string="Level Name", required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Active", default=True)

    user_ids = fields.Many2many(
        "res.users",
        "vendor_approval_level_user_rel",
        "level_id",
        "user_id",
        string="Approvers",
    )
