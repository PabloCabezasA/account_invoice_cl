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

from openerp import fields, models

class account_journal(models.Model):
    _inherit = 'account.journal'
    code_sii =  fields.Selection([
                                ('33','Facturación Eletrónica'),
                                ('34','Factura No Afecta o Exenta Electrónica'), 
                                ('43','Liquidación-Factura Electrónica'), 
                                ('46','Factura de Compra Electrónica'), 
                                ('52','Guía de Despacho Electrónica'),
                                ('56','Nota de Débito Electrónica'), 
                                ('61','Nota de Crédito Electrónica'),
                                ('110','Factura de Exportación'),
                                ('111','Nota de Débito de Exportación'),
                                ('112','Nota de Crédito de Exportación'),
                                ('39' ,'Boleta Electronica')
                                ], 'Codigo SII Chile', required=False)
    type_print = fields.Selection([
                                ('1','Facturación'),
                                ('2','Facturación Eletrónica'),
                                ('3','Facturación Eletrónica Termica'), 
                                ], 'Tipo de Impresion')
account_journal()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: