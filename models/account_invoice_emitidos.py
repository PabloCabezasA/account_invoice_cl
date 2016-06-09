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


class account_invoice_emitidos(models.Model):
    _name =  'account.invoice.emitidos'
    invoice = fields.Many2one('account.invoice', 'N° Factura')
    date = fields.Date('Fecha Facturación')
    code_sii = fields.Selection([
                                ('33','Facturación Eletrónica'),
                                ('34','Factura No Afecta o Exenta Electrónica'), 
                                ('43','Liquidación-Factura Electrónica'), 
                                ('46','Factura de Compra Electrónica'), 
                                ('52','Guía de Despacho Electrónica'),
                                ('56','Nota de Débito Electrónica'), 
                                ('61','Nota de Crédito Electrónica'),
                                ('110','Factura de Exportación'),
                                ('111','Nota de Débito de Exportación'),
                                ('112','Nota de Crédito de Exportación')
                                ], 'Tipo Documento')
    state = fields.Char('Estado Documento', size=200)
    folio = fields.Char('Folio', size=200)
    observacion = fields.Text('Obsrvacion')
    
    def create(self, cr, uid, data, context=None):
        res = super(account_invoice_emitidos, self).create(cr, uid, data, context=None)
        return res 
                
account_invoice_emitidos()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: