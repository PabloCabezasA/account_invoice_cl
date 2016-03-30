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
from amount_to_text_es import amount_to_text_es

class te_factura(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(te_factura, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'data_te': self._data_te,
            '_rut_emi': self._rut_emi,
            'rut_cli': self._rut_cli,
            'fac_det': self._fac_det,
            '_formato_numero': self._formato_numero,
            '_fecha_escrita' : self._fecha_escrita,
            '_amount_to_text':self._amount_to_text

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
    def _rut_emi(self, rut):
        if not rut:
            rut = ''
        rut = rut.lower().replace("cl", "")
        l = rut.__len__()
        if rut:
            vat = str(rut[l-l:l-7] + '.' + rut[l-7:l-4] + '.' + rut[l-4:l-1] + '-' + rut[l-1:l])
            return vat
        return rut
    #Rut cliente
    def _rut_cli(self, ids):
        data = []
        rut_obj = self.pool.get('account.invoice').browse(self.cr, self.uid, ids)
        rut = rut_obj.partner_id.vat.lower().replace("cl", "")
        l = rut.__len__()
        values = {
                'rut' : str(rut[l-l:l-7] + '.' + rut[l-7:l-4] + '.' + rut[l-4:l-1] + '-' + rut[l-1:l])
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
            if self.name == 'factura_elect':
                name_prod = data[i]['name'][len(name_product)+3:].lower() if name_product else data[i]['name'].lower()
            else:
                name_prod = data[i]['name'][len(name_product)+3:44].lower()+'..' if name_product else data[i]['name'][:44].lower()+'..'
            data[i] = {
                    'codigo': name_product,
                    'descripcion': name_prod,
                    'unidad_medida': data[i]['uos_id'][1],
                    'cantidad': int(data[i]['quantity']),
                    'p_unitario': data[i]['price_unit'],
                    'porcentaje': data[i]['discount'],
                    'valor': str(data[i]['price_subtotal']),
            }
        return data
    
    def _formato_numero(self, numero):
        while '/' in numero:
            numero=numero[numero.index('/')+1:]
            print numero
        return numero

    def _fecha_escrita(self, date): 
        fecha=''
        dia=''
        mes=''
        mes_string=''
        ano=''
        date_ready=''
        sep_dia='   '
        sep_mes='   '
        if date:
            fecha=str(date)
            mes=fecha[3:5]
            ano=fecha[6:10]
            dia=fecha[0:2]
            if mes == '01':
                mes_string='Enero     '
            elif mes == '02':
                mes_string='Febrero   '
            elif mes == '03':
                mes_string='Marzo     '
            elif mes == '04':
                mes_string='Abril     '
            elif mes == '05':
                mes_string='Mayo      '
            elif mes == '06':
                mes_string='Junio     '
            elif mes == '07':
                mes_string='Julio     '
            elif mes == '08':
                mes_string='Agosto    '
            elif mes == '09':
                mes_string='Septiembre'
            elif mes == '10':
                mes_string='Octubre   '
            elif mes == '11':
                mes_string='Noviembre '
            elif mes == '12':
                mes_string='Diciembre '
        date_ready=dia+sep_dia+mes_string+sep_mes+ano                   
        return date_ready

    def _amount_to_text(self, amount):
        text=''
        currency = 'Peso'
        text = amount_to_text_es(amount, currency)
        return 'SON: '+text



try:    
    report_sxw.report_sxw('report.factura_elect','account.invoice','addons/account_invoice_cl/report/factura_electronica.rml', parser=te_factura, header=False)
    report_sxw.report_sxw('report.factura_elec_t','account.invoice','addons/account_invoice_cl/report/factura_electronica_t.rml', parser=te_factura, header=False)
    report_sxw.report_sxw('report.factura_elec_n_t','account.invoice','addons/account_invoice_cl/report/factura_electronica_chiledar.rml', parser=te_factura, header=False)
except:
    print 'ya instalado'
#report_sxw.report_sxw('report.factura_elec','account.invoice','addons/account_invoice_cl/report/factura_electronica.rml', parser=te_factura, header='external')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
