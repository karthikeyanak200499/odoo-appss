from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    vendor_approval_group_id = fields.Many2one(
        "vendor.approval.group",
        string="Vendor Approval Group",
        tracking=True,
        help="Choose approval workflow group for this vendor.",

    )
    vendor_current_approval_level_id = fields.Many2one(
        "vendor.approval.level",
        string="Current Vendor Approval Level",
        tracking=True,
        copy=False,
    )
    vendor_approval_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Vendor Approval Status",
        default="draft",
        tracking=True,
        copy=False,
    )
    vendor_approval_line_ids = fields.One2many(
        "vendor.approval.matrix",
        "res_partner_id",
        string="Vendor Approval History",
        copy=False,
    )
    vendor_is_current_approver = fields.Boolean(
        compute="_compute_vendor_is_current_approver",
        store=False,
    )
    vendor_pending_at = fields.Char(
        string="Pending At",
        compute="_compute_vendor_pending_at",
        store=False,
    )
    vendor_attachment_count = fields.Integer(
        string="Attachment Count",
        compute="_compute_vendor_attachment_count",
        store=False,
    )

    def get_res_partner_url(self):
        self.ensure_one()
        base_url = (self.get_base_url() or "").rstrip("/")
        return f"{base_url}/web#id={self.id}&model=res.partner&view_type=form"

    def _compute_vendor_attachment_count(self):
        Attachment = self.env["ir.attachment"].sudo()
        for rec in self:
            rec.vendor_attachment_count = Attachment.search_count([
                ("res_model", "=", "res.partner"),
                ("res_id", "=", rec.id),
            ])

    def _compute_vendor_is_current_approver(self):
        for rec in self:
            rec.vendor_is_current_approver = False
            line = rec.vendor_current_approval_level_id
            if rec.vendor_approval_state == "pending" and line and line.active:
                rec.vendor_is_current_approver = self.env.user.id in line.user_ids.ids

    def _compute_vendor_pending_at(self):
        for rec in self:
            names = ""
            line = rec.vendor_current_approval_level_id
            if rec.vendor_approval_state == "pending" and line and line.active:
                names = ", ".join(line.user_ids.mapped("name"))
            rec.vendor_pending_at = names

    @api.onchange("vendor_approval_group_id")
    def _onchange_vendor_approval_group_id(self):
        for rec in self:
            if rec.vendor_approval_state in ("draft", "rejected"):
                rec.vendor_approval_line_ids = [(5, 0, 0)]
                rec.vendor_current_approval_level_id = False

    def _get_vendor_next_approval_level(self):
        self.ensure_one()
        if not self.vendor_approval_group_id:
            return False

        levels = self.vendor_approval_group_id.level_ids.filtered(
            lambda l: l.active
        ).sorted(key=lambda l: l.sequence)

        if not levels:
            return False

        if self.vendor_current_approval_level_id:
            current_seq = self.vendor_current_approval_level_id.sequence
            for level in levels:
                if level.sequence > current_seq:
                    return level
            return False

        return levels[0]

    def _vendor_notify_users(self, users, template_xmlid, subject=None):
        self.ensure_one()
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        users = users.filtered(lambda u: u.partner_id.email)

        if not template or not users:
            return False

        email_values = {
            "subject": subject or "",
            "email_to": ",".join(users.mapped("partner_id.email")),
        }

        try:
            template.with_context(
                approver_users=users,
                approver_names=", ".join(users.mapped("name")),
                approval_level=self.vendor_current_approval_level_id,
            ).send_mail(
                self.id,
                force_send=True,
                email_values=email_values,
            )
            return True
        except Exception:
            self.message_post(
                body=_("Vendor approval notification could not be emailed. Please review this vendor manually."),
                subtype_xmlid="mail.mt_note",
            )
            return False

    def action_vendor_submit_for_approval(self):
        for rec in self:
            if (rec.supplier_rank or 0) <= 0:
                raise UserError(_("This partner is not a Vendor."))

            if not rec.vendor_approval_group_id:
                raise UserError(_("Please choose Vendor Approval Group."))

            if rec.vendor_approval_state in ("pending", "approved"):
                continue

            first_level = rec._get_vendor_next_approval_level()
            if not first_level:
                raise UserError(_("No active approval levels found in Vendor Approval Group."))

            rec.write({
                "vendor_approval_state": "pending",
                "vendor_current_approval_level_id": first_level.id,
            })

            self.env["vendor.approval.matrix"].create({
                "res_partner_id": rec.id,
                "company_id": rec.company_id.id,
                "approval_level_id": first_level.id,
                "level": first_level.sequence,
                "approver_user_id": first_level.user_ids[:1].id if first_level.user_ids else False,
                "user_id": self.env.user.id,
                "action": "requested",
                "notes": "Vendor approval requested",
            })

            if first_level.user_ids:
                rec._vendor_notify_users(
                    first_level.user_ids,
                    "vendor_group_approval.mail_template_vendor_stage_request",
                    subject=_("Vendor Approval Needed - %s") % (rec.name or ""),
                )

    def action_vendor_approve(self):
        for rec in self:
            if rec.vendor_approval_state != "pending":
                continue

            current_level = rec.vendor_current_approval_level_id
            if not current_level:
                raise UserError(_("Current vendor approval level not found."))

            if self.env.user.id not in current_level.user_ids.ids:
                raise UserError(_("You are not allowed to approve at this level."))

            self.env["vendor.approval.matrix"].create({
                "res_partner_id": rec.id,
                "company_id": rec.company_id.id,
                "approval_level_id": current_level.id,
                "level": current_level.sequence,
                "approver_user_id": self.env.user.id,
                "user_id": self.env.user.id,
                "action": "approved",
                "approved_by": self.env.user.id,
                "approved_on": fields.Datetime.now(),
                "approved_signature_html": self.env.user.signature or "",
                "notes": "Approved",
            })

            next_level = rec._get_vendor_next_approval_level()

            if not next_level:
                rec.write({
                    "vendor_approval_state": "approved",
                    "vendor_current_approval_level_id": False,
                })

                notify_users = self.env["res.users"]
                if rec.create_uid:
                    notify_users |= rec.create_uid
                notify_users |= rec.vendor_approval_group_id.level_ids.filtered(lambda l: l.active).mapped("user_ids")

                rec._vendor_notify_users(
                    notify_users,
                    "vendor_group_approval.mail_template_vendor_final_approved",
                    subject=_("Vendor Approved - %s") % (rec.name or ""),
                )
            else:
                rec.write({
                    "vendor_approval_state": "pending",
                    "vendor_current_approval_level_id": next_level.id,
                })

                rec._vendor_notify_users(
                    next_level.user_ids,
                    "vendor_group_approval.mail_template_vendor_stage_request",
                    subject=_("Vendor Approval Needed - %s") % (rec.name or ""),
                )

    def action_vendor_reject(self):
        for rec in self:
            if rec.vendor_approval_state != "pending":
                continue

            current_level = rec.vendor_current_approval_level_id
            if not current_level:
                raise UserError(_("Current vendor approval level not found."))

            if self.env.user.id not in current_level.user_ids.ids:
                raise UserError(_("You are not allowed to reject at this level."))

            self.env["vendor.approval.matrix"].create({
                "res_partner_id": rec.id,
                "company_id": rec.company_id.id,
                "approval_level_id": current_level.id,
                "level": current_level.sequence,
                "approver_user_id": self.env.user.id,
                "user_id": self.env.user.id,
                "action": "rejected",
                "approved_by": self.env.user.id,
                "approved_on": fields.Datetime.now(),
                "notes": _("Rejected by %s") % self.env.user.name,
            })

            rec.write({
                "vendor_approval_state": "rejected",
                "vendor_current_approval_level_id": False,
            })

            notify_users = self.env["res.users"]
            if rec.create_uid:
                notify_users |= rec.create_uid
            notify_users |= rec.vendor_approval_group_id.level_ids.filtered(lambda l: l.active).mapped("user_ids")

            rec._vendor_notify_users(
                notify_users,
                "vendor_group_approval.mail_template_vendor_rejected",
                subject=_("Vendor Rejected - %s") % (rec.name or ""),
            )
