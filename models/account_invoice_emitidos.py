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
from openerp.osv import fields, osv
from lxml import objectify
import base64
from openerp.addons.account_invoice_cl.connect.connect import *
from openerp.addons.account_invoice_cl.connect.connect import _connect_soap

class account_invoice_emitidos(osv.osv):
    _name = 'account.invoice.emitidos'
    _columns = {
        'invoice': fields.many2one('account.invoice', 'N° Factura'),
        'date': fields.date('Fecha Facturación'),
        'code_sii': fields.selection([
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
                            ], 'Tipo Documento'),
        'state': fields.char('Estado Documento', size=200),
        'folio': fields.char('Folio', size=200),
        'observacion': fields.text('Obsrvacion'),
    }
    
    def create(self, cr, uid, data, context=None):
        res = super(account_invoice_emitidos, self).create(cr, uid, data, context=None)
        return res 
    
    def _fetch_document(self, cr, uid, context=None):
        return True
        partner_vat = self.pool.get('res.partner').read(cr, uid, [uid], ['vat'])[0]['vat']
        obj_partner = self.pool.get('account.invoice.emitidos')
        emitidos_id = obj_partner.search(cr, uid, [('state','=', 'encolado'),])
        lineas_read = obj_partner.read(cr, uid, emitidos_id,['invoice','code_sii'])
        #Conexión firmador
        client = _connect_soap(self, cr, uid, uid)
        for i in range(lineas_read.__len__()):
            #Envia documento a firmar
            res = client.service.consultarDocumento('76252252-7',lineas_read[i]['code_sii'], lineas_read[i]['invoice'][1]) #Consulta Documento
            xml = base64.b64encode(res.documentos.documento[0].xml)
            id = lineas_read[i]['invoice'][0]
            name = lineas_read[i]['invoice'][1]
            values = ({
                       'factura_firmada': xml,
                       'nombre_factura': name,
            })
            self.pool.get('account.invoice').write(cr,uid, [id], values)
            self.pool.get('account.invoice.emitidos').write(cr, uid, [emitidos_id[i]], {'state': 'firmado'})
            
account_invoice_emitidos()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: