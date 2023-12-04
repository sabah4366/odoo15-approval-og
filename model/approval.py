from odoo import models, fields, api ,http
class PurchaseApproval(models.Model):
    _name = 'purchase.approval'
    _description = 'Purchase Approval'
    _rec_name = "approval"

    approval = fields.Char(string='Approval')
    approval_model_id = fields.Many2many('ir.model', string='Model')
    approval_levels = fields.Integer(string='Levels of Approval', default=1)
    need_approval = fields.Boolean(string='Need Approval', default=True)
    level_ids = fields.One2many('purchase.approval.level', 'approval_id', string='Approval Levels')

    @api.onchange('approval_levels')
    def _onchange_approval_levels(self):
        """Generate approval levels based on the 'Levels of Approval' field."""
        if self.approval_levels > 0:
            self.level_ids = [(5, 0, 0)]

            new_levels = []
            for level in range(1, self.approval_levels + 1):
                self.level_ids = [(0, 0, {
                    'level': f'Level {level}',
                })]
                self.level_ids = new_levels


class PurchaseApprovalLevel(models.Model):
    _name = 'purchase.approval.level'
    _description = 'Purchase Approval Level'

    approval_id = fields.Many2one('purchase.approval', string='Approval')
    level = fields.Char(string='Level')
    user_ids = fields.Many2many('res.users', string='Approvers')
    order_id = fields.Many2one('purchase.order', string="Purchase Order")


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def get_estimation_approve(self):
        approve = self.env['purchase.approval'].sudo().search([('approval_model_id', '=', 'purchase.order')], limit=1)
        if approve and approve.need_approval and approve.approval_levels > 0 and approve.level_ids:
            return True
        else:
            return False

    is_approver = fields.Boolean(string='Is Approver', compute='_compute_is_approver')
    is_approved = fields.Boolean(string='Is Approved', compute='_compute_is_approved')
    # state = fields.Selection([
    #     ('draft', 'RFQ'),
    #     ('sent', 'RFQ Sent'),
    #     ('waiting for approval', 'Waiting forApproval'),
    #     ('approved', 'Approved'),
    #     ('approve', 'Approved'),
    #     ('purchase', 'Purchase Order'),
    #     ('done', 'Locked'),
    #     ('cancel', 'Cancelled')
    # ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('waiting for approval', 'Waiting forApproval'),
        ('approved', 'Approved'),
        ('approve', 'PO Approved'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
        ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)


    approver_id = fields.Many2many('res.users',
                                   string="Approvers",
                                   default=lambda self: self.get_level_approvers())


    is_hide_button_for_user = fields.Boolean(string='Is Approved ')
    is_need_approve = fields.Boolean(string="Need Approve", default=lambda self: self.get_estimation_approve())



    def _compute_is_approver(self):
        for record in self:
            record.is_approver = True if self.env.user.id in record.approver_id.ids else False

    @api.model
    def _compute_is_approved(self):
        approval_model = self.env['purchase.approval.level']
        lgn_user = http.request.env.user
        existing_approval = approval_model.search([('order_id', '=', self.id), ('user_ids', 'in', lgn_user.id)])
        if existing_approval:
            for record in self:
                if existing_approval.user_ids.id == lgn_user.id:
                    record.is_approved = True
                else:
                    record.is_approved = False
        else:
            self.is_approved = False




    @api.model
    def get_level_approvers(self):
        approver_ids = []
        approval_model = self.env['purchase.approval'].sudo().search(
            [('approval_model_id', '=', 'purchase.order')], limit=1)
        if approval_model:
            for level in approval_model.level_ids:
                if isinstance(level.user_ids, int):  # Check if user_ids is an ID
                    user_ids = [level.user_ids]
                else:
                    user_ids = level.user_ids.ids
                approver_ids += [(4, user_id) for user_id in user_ids]
        return approver_ids

    def button_submit_for_approval(self):
        approval_model = self.env['purchase.approval.level']
        lgn_user = http.request.env.user


        existing_approval = approval_model.search([('order_id', '=', self.id), ('user_ids', 'in', lgn_user.id)])
        if not existing_approval:
            # Create a new approval record for the user
            approval_model.create({
                'order_id': self.id,
                'user_ids': [(4, lgn_user.id)],
            })

        # Check if all approvers have approved
        self._compute_is_approved()
        approvals_count = approval_model.search_count([('order_id', '=', self.id)])
        if approvals_count == len(self.approver_id):
            self.write({'state': 'approve'})

        return True


    def button_confirm(self):
        if not self.approver_id:
            super(PurchaseOrder,self).button_confirm()
        else:
            for order in self:
                order._add_supplier_to_product()
                # Deal with double validation process
                if order._approval_allowed():
                    order.button_approve()
                else:
                    order.write({'state': 'to approve'})
                if order.partner_id not in order.message_partner_ids:
                    order.message_subscribe([order.partner_id.id])
            return True



    def sent_for_approval(self):
        self.state='waiting for approval'

    def button_cancel(self):
        res = super(PurchaseOrder,self).button_cancel()
        self.state='cancel'
        return res