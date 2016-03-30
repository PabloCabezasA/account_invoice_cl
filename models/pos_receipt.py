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

from openerp.osv import fields,osv
from openerp.tools.translate import _
import datetime
from datetime import date
import time
import base64 , os
from elaphe import barcode

class pos_receipt(osv.osv_memory):
    _inherit = 'pos.receipt'
    

    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        id = context.get('active_ids', [])
        if id :
            order = self.pool.get('pos.order').browse(cr,uid,id[0])
            self.xml_create(cr, uid, order.id)
        res = super(pos_receipt, self).print_report(cr, uid, ids, context)
        return res
    
    def xml_create(self,cr, uid, ids):
        xml_data = self.pool.get('pos.order').browse(cr, uid, ids)        
        if xml_data.sale_journal.code_sii == '39':
            #Codificacion 
            xml_factura ='<?xml version="1.0" ?>'
            xml_factura += '<EnvioDTE xmlns="http://www.sii.cl/SiiDte" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sii.cl/SiiDte EnvioDTE_v10.xsd" version="1.0">'
            xml_factura += '<SetDTE ID="SetDoc">'
            xml_factura += '<Caratula version="1.0">'
            xml_factura += '<RutEmisor>76252252-7</RutEmisor>'
            xml_factura += '<RutEnvia>76252252-7</RutEnvia>'
            xml_factura += '<RutReceptor>'+self.validar_rut(xml_data.partner_id.vat)+'</RutReceptor>'
            xml_factura += '<FchResol>'+date.today().strftime('%Y-%m-%d')+'</FchResol>'
            xml_factura += '<NroResol>0</NroResol>'
            xml_factura += '<TmstFirmaEnv>'+date.today().strftime('%Y-%m-%d')+'T'+str(time.strftime("%H:%M:%S"))+'</TmstFirmaEnv>'
            xml_factura += '<SubTotDTE>'
            xml_factura += '<TpoDTE>' + xml_data.sale_journal.code_sii + '</TpoDTE>'
            xml_factura += '<NroDTE>1</NroDTE>'
            xml_factura += '</SubTotDTE>'
            xml_factura += '</Caratula>'
            xml_factura += '<DTE version="1.0">'
            xml_factura += '<Documento ID="E000000001T033F0002089942">' #Identificador único del DTE #Datos de Prueba            
            #Detalle por linea de Factura     
            i = 1
            for record in xml_data.lines: 
                xml_factura += '<Detalle>'
                xml_factura += '<NroLinDet>' + str(i) + '</NroLinDet>' + '<CdgItem>'
                xml_factura += '<TpoCodigo>' + 'INT1' + '</TpoCodigo>'  
                xml_factura += '<VlrCodigo>' + self.limpiar_campo_guion(record.product_id.default_code) + '</VlrCodigo>' + '</CdgItem>'
                xml_factura += '<NmbItem>' + record.product_id.name + '</NmbItem>'
                xml_factura += '<DscItem>' + str(int(record.discount if record.discount else 0 )) + '</DscItem>'
                xml_factura += '<QtyItem>' + str(int(record.qty)) + '</QtyItem>'
                xml_factura += '<PrcItem>' + str(int(record.price_unit)) + '</PrcItem>'
                #monto_item = (int(record['price_unit']*record['quantity'])) * (1+(record['discount']/100))
                xml_factura += '<MontoItem>' + str(int(record.price_subtotal_incl)) + '</MontoItem>'
                xml_factura += '</Detalle>'
            
                if i == 1:
                    product_te = record.product_id.name
                i += 1
#            xml_factura += '<Referencia>'            
#            xml_factura +='<NroLinRef>1</NroLinRef>'
#            xml_factura +='<TpoDocRef>SET</TpoDocRef>'
#            xml_factura +='<FolioRef>'+ self.limpiar_campo_slash(xml_data.name) + '</FolioRef>'
#            xml_factura +='<FchRef>2015-04-07</FchRef>'
#            xml_factura +='<RazonRef>CASO 357045-1</RazonRef>'
#            xml_factura += '</Referencia>'
            #Timbre Electronico (DTE)
            #Detalle Emisor y Receptor
            te_factura = '<TED version="1.0">'
            te_factura += '<DD>' + '<RE>' + self.validar_rut(xml_data.company_id.vat) +'</RE>'
            te_factura += '<TD>' + xml_data.sale_journal.code_sii + '</TD>'
            te_factura += '<F>' + self.limpiar_campo_slash(xml_data.name) + '</F>'#folio
            te_factura += '<FE>' + xml_data.date_order + '</FE>'#fecha emision
            te_factura += '<RR>' + self.validar_rut(xml_data.partner_id.vat) + '</RR>'
            te_factura += '<RSR>' + xml_data.company_id.name + '</RSR>'
            te_factura += '<MNT>' + str(int(xml_data.amount_total)) + '</MNT>'
            te_factura += '<IT1>' + product_te + '</IT1>'
            #Codigo de Autorizacion de Folios
            te_factura += '<CAF version="1.0">' + '<DA>'
            te_factura += '<RE>' + self.validar_rut(xml_data.company_id.vat) + '</RE>'
            te_factura += '<RS>' + xml_data.company_id.name + '</RS>'
            te_factura += '<TD>' + xml_data.sale_journal.code_sii + '</TD>' + '<RNG>'
            te_factura += '<D>' + '2080001' + '</D>' #Rango de folios autorizados por SII Desde #Datos de Prueba
            te_factura += '<H>' + '2090000' + '</H>' + '</RNG>' #Rango de folios autorizados por SII Hasta #Datos de Prueba
            te_factura += '<FA>' + '2013-02-28' + '</FA>' + '<RSAPK>' #Fecha en que fue aprobado el rango de folios #Datos de Prueba
            te_factura += '<M>' + '13YaiuWAQzaPYkj6I7T81SMKpZDqrmB1nKyYJHtr9L6jHlmUBq3nPmZgc7M3n9F6CgJo8y0akeRksqD023tUlw==' + '</M>' #Valor Modulo RSA #Datos de Prueba
            te_factura += '<E>' + 'Aw==' +'</E>' + '</RSAPK>' #Valor Exponente RSA #Datos de Prueba
            te_factura += '<IDK>' + '300' + '</IDK>' + '</DA>' #Identificador llave pública #Datos de Prueba
            te_factura += '<FRMA algoritmo="SHA1withRSA">' + 'hIR/4lqBMlA2954ktS8+v4jNU+VtO2HHKXyVFlClvrDsPXP1985KACQihW6HAz6ZqcuXIUOjutCOv+GEVG84oA==' + '</FRMA>'
            te_factura += '</CAF>' #Firma generada en SHA1 #Datos de Prueba
            te_factura += '<TSTED>' +date.today().strftime('%Y-%m-%d')+'T'+str(time.strftime("%H:%M:%S"))+ '</TSTED>' + '</DD>'
            te_factura += '<FRMT algoritmo="SHA1withRSA">' + 'JMQui+OsngKgNVybQNQfd6/4Jm2xvyUkWhLisEydnqhNlxu+JFJIp+wbJIIHjTbebc6Fy4E+YS1B8yqL6+MqrA==' + '</FRMT>' #Firma generada en SHA1 #Datos de Prueba
            te_factura += '</TED>' #Fin (DTE)
            
            xml_factura += te_factura
            xml_factura += '<TmstFirma>' + date.today().strftime('%Y-%m-%d')+'T'+str(time.strftime("%H:%M:%S")) + '</TmstFirma>' + '</Documento>'              
#            xml_factura += '<Signature xmlns="http://www.w3.org/2000/09/xmldsig#"></Signature>'
            xml_factura += '</DTE>'+'</SetDTE>'
#            xml_factura +='<Signature xmlns="http://www.w3.org/2000/09/xmldsig#"></Signature>'
            xml_factura +='</EnvioDTE>'
            
#            firma = self.firmar_documento(cr,uid,ids,xml_factura)
            self.funcion_pdf47(cr,uid,xml_data.id,te_factura)
#            xml_factura=self.insertar_firma_en_xml(firma, xml_factura)
#            xml = self.validar_shema(xml_factura)
        else:
            raise openerp.exceptions.Warning('Funcion solo para Diarios tipo boleta electronica de sii')
    
    
    def funcion_pdf47(self,cr,uid,ids,te_factura):
        #PDF417
        #path = os.getcwd() + '/openerp/addons/account_invoice_cl/%s'
        path = os.getcwd() + '/openerp/trunk/account_invoice_cl/%s'
        barcode('pdf417', te_factura, options=dict(eclevel=5, columns=15, rows=15), scale=2, data_mode='8bits').save(path % 'te_factura.png')
        with open(path % 'te_factura.png', "rb") as image_file:
            binary = base64.b64encode(image_file.read())
            self.pool.get('pos.order').write(cr, uid, ids,{'te_electronico': binary})
            os.remove(path % 'te_factura.png')

    def limpiar_campo_slash(self,numero):
        while str(numero).find('/') >= 0:
            position =0
            position = str(numero).find('/')
            numero = numero[position+1:]            
        return numero
        
    def validar_rut(self,rut):
        vat = ""
        cont = 0
        if rut and len(rut) > 0 :
            for r in rut:
                cont += 1
                if not r.isalpha() and not r == '.' and not r == '-':   
                    vat +=r
                elif cont == len(rut):
                    vat +=r
        else: return '66.666.666-6'
        return str(str(vat[:len(vat)-1])+'-'+vat[len(vat)-1]).strip()

    def limpiar_campo_guion(self,numero):
        while str(numero).find('-') >= 0:
            position =0
            position = str(numero).find('-')
            numero = numero[position+1:]            
        return numero

pos_receipt()

class pos_order(osv.osv):    
    _inherit = "pos.order"    
        
    _columns = {   
        'te_electronico': fields.binary('te_electronico'), #Xml base para construir PDF417
        'mem_sii': fields.char('N° SII', size=5),
    }
pos_order()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: