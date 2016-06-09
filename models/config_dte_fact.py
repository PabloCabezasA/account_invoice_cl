# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields

class config_dte_invoice(models.Model):
    _name="config.dte.invoice"
    account_client_default = fields.Many2one('account.account', 'Cuenta cliente', required=True, readonly=False, help="Cuenta que se usa para la generacion de las lineas de la factura.")
    account_proveedor_default = fields.Many2one('account.account', 'Cuenta proveedor', required=True, readonly=False, help="Cuenta que se usa para la generacion de las lineas de la factura.")
    iva_credito = fields.Many2one('account.tax', 'IVA CF', required=True, readonly=False)
    iva_debito = fields.Many2one('account.tax', 'IVA DF', required=True, readonly=False)
    state = fields.Boolean('Estado', help="muesta si es activo o inactivo")

config_dte_invoice()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:#
