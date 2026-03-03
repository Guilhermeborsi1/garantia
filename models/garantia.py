from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Garantia(models.Model):
    _name = 'garantia.garantia'
    _description = 'Garantia'
    name = fields.Char(string='Nome da Garantia', required=True)
    description = fields.Text(string='Descrição da Garantia')
    start_date = fields.Date(string='Data de Início', required=True)
    end_date = fields.Date(string='Data de Término', required=True)
    product_id = fields.Many2one('product.product', string='Produto', required=True)
    contract_archive = fields.Binary(string='Arquivo do Contrato')
    sight_archive = fields.Binary(string='Arquivo de Vistoria')
    contract_confirmation = fields.Boolean(string='Contrato Confirmado', default=False)
