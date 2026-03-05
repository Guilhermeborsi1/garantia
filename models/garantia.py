from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Garantia(models.Model):
    _name = 'garantia.garantia'
    _description = 'Garantia'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nome da Garantia', required=True, tracking=True)
    user_ir_id = fields.Many2one('res.users', string='Responsável', required=True, tracking=True)
    description = fields.Text(string='Descrição da Garantia', tracking=True)
    start_date = fields.Date(string='Data de Início', required=True, tracking=True)
    end_date = fields.Date(string='Data de Término', required=True, tracking=True)
    product_id = fields.Many2one('product.product', string='Produto', required=True, tracking=True)

    contract_archive = fields.Binary(string='Arquivo do Contrato')
    sight_archive = fields.Binary(string='Arquivo de Vistoria')
    contract_confirmation = fields.Boolean(string='Contrato Confirmado', default=False, tracking=True)

    @api.constrains('end_date', 'start_date')
    def _check_end_date(self):
        for record in self:
            if record.end_date and record.start_date and record.end_date < record.start_date:
                raise ValidationError('A data de término deve ser posterior à data de início.')

    # ----------------------------
    # CHATTER: mensagem quando vence hoje
    # ----------------------------
    def _post_expiry_message_if_needed(self):
        """Posta no chatter quando vence hoje (evita spam: 1x por dia por registro)."""
        today = fields.Date.context_today(self)

        for warranty in self:
            if not warranty.end_date or warranty.end_date != today:
                continue
            if not warranty.user_ir_id or not warranty.user_ir_id.partner_id:
                continue

            tag = f"[GARANTIA_VENCE_HOJE:{today}]"
            if warranty.message_ids.filtered(lambda m: tag in (m.body or "")):
                continue

            warranty.message_post(
                body=_(
                    "%(tag)s A garantia <b>%(name)s</b> do produto <b>%(product)s</b> vence hoje (%(date)s).",
                    tag=tag,
                    name=warranty.name or "",
                    product=warranty.product_id.display_name or "",
                    date=today.strftime('%d/%m/%Y'),
                ),
                subtype_xmlid="mail.mt_note",
                partner_ids=[warranty.user_ir_id.partner_id.id],
            )

    # ----------------------------
    # ATIVIDADES (3 ETAPAS)
    # ----------------------------
    def _todo_activity_type(self):
        return self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)

    def _activity_exists(self, summary):
        """Evita duplicar atividade ativa com o mesmo summary (Odoo 19: não usar state)."""
        self.ensure_one()
        Activity = self.env['mail.activity'].sudo()
        todo = self._todo_activity_type()
        if not todo:
            return False

        domain = [
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('activity_type_id', '=', todo.id),
            ('summary', '=', summary),
            ('active', '=', True),
        ]
        if 'date_done' in Activity._fields:
            domain.append(('date_done', '=', False))

        return bool(Activity.search_count(domain))

    def _schedule_activity(self, summary, note, deadline_date):
        self.ensure_one()
        todo = self._todo_activity_type()
        if not todo or not self.user_ir_id:
            return
        if self._activity_exists(summary):
            return

        self.activity_schedule(
            activity_type_id=todo.id,
            user_id=self.user_ir_id.id,
            summary=summary,
            note=note,
            date_deadline=deadline_date,
        )

    def _ensure_expiry_activities(self, days=5):
        today = fields.Date.context_today(self)

        for rec in self:
            if not rec.end_date or not rec.user_ir_id:
                continue

            limit_date = today + timedelta(days=days)
            product = rec.product_id.display_name or ''
            end_str = rec.end_date.strftime('%d/%m/%Y')

            if rec.end_date < today:
                summary = "Garantia vencida"
                note = _("A garantia '%(name)s' do produto '%(product)s' venceu em %(date)s.",
                         name=rec.name or '', product=product, date=end_str)
                rec._schedule_activity(summary, note, today)

            elif rec.end_date == today:
                summary = "Garantia vence hoje"
                note = _("A garantia '%(name)s' do produto '%(product)s' vence hoje (%(date)s).",
                         name=rec.name or '', product=product, date=end_str)
                rec._schedule_activity(summary, note, today)

            elif rec.end_date <= limit_date:
                summary = "Garantia a vencer"
                note = _("A garantia '%(name)s' do produto '%(product)s' vence em %(date)s (faltam poucos dias).",
                         name=rec.name or '', product=product, date=end_str)
                rec._schedule_activity(summary, note, rec.end_date)

    # ----------------------------
    # CREATE / WRITE
    # ----------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ensure_expiry_activities(days=5)
        records._post_expiry_message_if_needed()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'end_date' in vals or 'user_ir_id' in vals:
            self._ensure_expiry_activities(days=5)
            self._post_expiry_message_if_needed()
        return res

    # ----------------------------
    # CRON
    # ----------------------------
    @api.model
    def cron_check_warranty_dates(self):
        """Cron: garante atividades e posta no chatter quando vence hoje."""
        today = fields.Date.context_today(self)
        limit_date = today + timedelta(days=5)

        recs = self.search([
            ('end_date', '!=', False),
            ('user_ir_id', '!=', False),
            ('end_date', '<=', limit_date),
        ])
        recs._ensure_expiry_activities(days=5)

        today_recs = recs.filtered(lambda r: r.end_date == today)
        today_recs._post_expiry_message_if_needed()