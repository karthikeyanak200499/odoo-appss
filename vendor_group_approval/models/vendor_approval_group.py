from odoo import models, fields


class VendorApprovalGroup(models.Model):
    _name = "vendor.approval.group"
    _description = "Vendor Approval Group"
    _order = "sequence, id"

    name = fields.Char(string="Group Name", required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Active", default=True)

    level_ids = fields.One2many(
        "vendor.approval.level",
        "group_id",
        string="Approval Levels",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
