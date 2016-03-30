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

import time
from report import report_sxw
from osv import osv, orm
from elaphe import barcode
import base64, os

class te_factura(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(te_factura, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'data_te': self._data_te,
            'rut_emi': self._rut_emi,
            'rut_cli': self._rut_cli,
            'fac_det': self._fac_det,
        })
    #Timbre Electronico
    def _data_te(self, ids):
        data = []
        te_factura = self.pool.get('account.invoice').read(self.cr, self.uid, ids,['te_factura'])['te_factura']
        values = {
                'img' : te_factura
        }
        data.append(values)
        return data
    #Rut Emisor
    def _rut_emi(self, ids):
        data = []
        rut_obj = self.pool.get('account.invoice').browse(self.cr, self.uid, ids)
        rut = rut_obj.company_id.partner_id.vat.replace("CL", "")
        l = rut.__len__()
        values = {
                'rut' : rut[l-l:l-7] + '.' + rut[l-7:l-4] + '.' + rut[l-4:l-1] + '-' + rut[l-1:l]
        }
        data.append(values)
        return data
    #Rut cliente
    def _rut_cli(self, ids):
        data = []
        rut_obj = self.pool.get('account.invoice').browse(self.cr, self.uid, ids)
        rut = rut_obj.partner_id.vat.replace("CL", "")
        l = rut.__len__()
        values = {
                'rut' : rut[l-l:l-7] + '.' + rut[l-7:l-4] + '.' + rut[l-4:l-1] + '-' + rut[l-1:l]
        }
        data.append(values)
        return data
    #Detalle Factura
    def _fac_det(self, ids):
        data = []
        rut_obj = self.pool.get('account.invoice.line')
        detalle_ids = rut_obj.search(self.cr, self.uid, [('invoice_id', '=', ids),])
        data = rut_obj.read(self.cr,self.uid,detalle_ids)
        for i in range (int(data.__len__())):
            name_product = self.pool.get('product.product').read(self.cr,self.uid,[data[i]['product_id'][0]],['default_code'])[0]['default_code']
            data[i] = {
                    'codigo': name_product,
                    'descripcion': data[i]['name'],
                    'unidad_medida': data[i]['uos_id'][1],
                    'cantidad': data[i]['quantity'],
                    'p_unitario': data[i]['price_unit'],
                    'porcentaje': data[i]['discount'],
                    'valor': str(data[i]['price_subtotal']),
            }
        return data
try:
    report_sxw.report_sxw('report.factura_ced','account.invoice','addons/account_invoice_cl/report/factura_cedible.rml', parser=te_factura, header='external')
except:
    'ya instalado'
#report_sxw.report_sxw('report.factura_ced','account.invoice','addons/account_invoice_cl/report/factura_cedible.rml', parser=te_factura, header='external')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: