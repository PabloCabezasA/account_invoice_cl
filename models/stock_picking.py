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
from lxml import etree
from datetime import date
from elaphe import barcode
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email import encoders

import openerp.exceptions
import xml.etree.ElementTree as ET
import datetime
import time
import base64 , os
import smtplib
import unicodedata
import json
import logging
_logger = logging.getLogger(__name__)

class stock_journal(osv.osv):
    _inherit = 'stock.journal'
    _columns = {
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
                            ('112','Nota de Crédito de Exportación'),
                            ('39' ,'Boleta Electronica')
                            ], 'Codigo SII Chile', required=False),
    }
stock_journal()

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    _columns = {
                'xml_file': fields.binary('xml firmado'), 
                'export_filename': fields.char('nombre xml', size=200),
                'trackid' : fields.char('trackid', size=200),
                'id_documento' : fields.char('Documento Unico', size=200),
                'razonref' : fields.char('Razon ref', size=200),
                'to_setest' : fields.boolean('Set de Prueba'),
                'indicador_bienes': fields.selection([
                            ('1', 'Operación constituye venta'),
                            ('2', 'Ventas por efectuar'), 
                            ('3', 'Consignaciones'), 
                            ('4', 'Entrega gratuita'), 
                            ('5', 'Traslados internos'),
                            ('6', 'Otros traslados no venta'), 
                            ('7', 'Guía de devolución'),
                            ('8', 'Traslado para exportación. (no venta)'),
                            ('9', 'Venta para exportación'),
                            ], 'Indicador Tipo de traslado de bienes', required=False),
    }

    def crear_archivo(self, xml, name_file):
        path = '/tmp/'+name_file
        archi=open(path,'a+b')
        archi.write(self.pool.get('account.invoice').special(xml))                                
        archi.close()
        return path


    def firmado_envio(self, cr, uid, picking, path, par_caf, par_firmador, modelo):
        data = self._info_for_facturador(cr, uid, picking, par_caf, par_firmador, path, modelo)
        if picking.to_setest:
            self.pool.get('firmador.firmador').firmar_dte_prueba_sii(cr, uid, [picking.id], data, context=None)        
        elif par_firmador.type_send == 'firmar_enviar':
            self.pool.get('firmador.firmador').firmar_enviar_sii(cr, uid, [picking.id], data, context=None)
        elif par_firmador.type_send == 'firmar':
            ted = self.pool.get('firmador.firmador').fimar_cliente(cr, uid, [picking.id], data, context=None)
        else:
            raise openerp.exceptions.Warning('Error al crear xml. Favor ingrasar campo tipo de envio en Firmador')
        return data

    
    def _info_for_facturador(self, cr, uid, picking, par_caf, par_firmador, path, objeto):
        data = {
                'document_id' : picking.id,
                'rutaxmldte': path,
                'rutacertpfx': par_firmador.pathcertificado + picking.company_id.export_filename,
                'contcertpxpfx': picking.company_id.p12pass, 
                'rutacaf':  par_firmador.pathfolio + par_caf.export_filename,
                'fecharesolucion': str(picking.company_id.fecharesolucion), 
                'nroresolucion': str(picking.company_id.nroresolucion), 
                'rutenvio': self.pool.get('account.invoice').validar_rut(picking.company_id.rutenvia), 
                'pathbase': par_firmador.pathbase, 
                'modelo' : objeto,
                }
        _logger.info('Enviando al Facturador Estos datos %s' % data)
        return data

    def validar_iva(self, cr, uid, picking):
        tax = {}
        for rec in picking.move_lines:
            for tx in rec.product_id.taxes_id:
                if tx.amount:
                    tax['amount'] = tx.amount
                    return tax
        return False    
    
stock_picking()

class stock_picking_out(osv.osv):
    _inherit = 'stock.picking.out'
    _columns = {
                'xml_file': fields.binary('xml firmado'), 
                'export_filename': fields.char('nombre xml', size=200),
                'trackid' : fields.char('trackid', size=200),
                'id_documento' : fields.char('Documento Unico', size=200),
                'razonref' : fields.char('razon Ref', size=200),
                'to_setest' : fields.boolean('Set de Prueba'),                
                'indicador_bienes': fields.selection([
                            ('1', 'Operación constituye venta'),
                            ('2', 'Ventas por efectuar'), 
                            ('3', 'Consignaciones'), 
                            ('4', 'Entrega gratuita'), 
                            ('5', 'Traslados internos'),
                            ('6', 'Otros traslados no venta'), 
                            ('7', 'Guía de devolución'),
                            ('8', 'Traslado para exportación. (no venta)'),
                            ('9', 'Venta para exportación'),
                            ], 'Indicador Tipo de traslado de bienes', required=False),

    }
    
    
    def print_picking_out(self, cr, uid, ids, context=None):
        self.xml_create(cr, uid, ids, context)
        return {
                'type'          : 'ir.actions.report.xml',
                'report_name'   : 'stock.picking.list.out',
                'header'        : True,                
                'datas': {
                    'model':'stock.picking.out',
                    'id': ids[0],
                    'ids': ids,
                    },
                'nodestroy': False
                }
        
    def crear_dte(self, cr, uid, ids , context=None):
        xml_data = self.browse(cr, uid, ids[-1], context)
        invoice_object = self.pool.get('account.invoice')
        picking_obj = self.pool.get('stock.picking')
        if not xml_data.id_documento:
            raise openerp.exceptions.Warning('Ingresar Campo id Documento')                                    
        if not xml_data.indicador_bienes:
            raise openerp.exceptions.Warning('Indicador Tipo de traslado de bienes')
        emisor_d = self.pool.get('res.partner').browse(cr, uid, xml_data.company_id.partner_id.id,)
        emisor_d = invoice_object.limpiar_campos_emisor_xml(cr, uid, emisor_d)
        invoice_object.limpiar_campos_receptor_xml(xml_data.partner_id)

        xml_picking = '<DTE version="1.0">'
        xml_picking += '<Documento ID="'+ xml_data.id_documento +'">' #Identificador único del DTE #Datos de Prueba            
        xml_picking += '<Encabezado>' + '<IdDoc>'        
        xml_picking += '<TipoDTE>' + xml_data.stock_journal_id.code_sii + '</TipoDTE>' #Dato de prueba
        xml_picking += '<Folio>' + invoice_object.limpiar_campo_slash(xml_data.name) + '</Folio>' #Dato de prueba deveria estar en el rango de folios
        xml_picking += '<FchEmis>' + xml_data.date[:10] + '</FchEmis>'
        xml_picking += '<IndTraslado>'+ xml_data.indicador_bienes +'</IndTraslado>'
        xml_picking += '<FchCancel>'+ xml_data.min_date[:10] +'</FchCancel>'
        xml_picking += '</IdDoc>' + '<Emisor>'
        
        xml_picking += '<RUTEmisor>'+invoice_object.validar_rut(xml_data.company_id.vat)+'</RUTEmisor>' #self.validar_rut(emisor_d['vat'])
        xml_picking += '<RznSoc>' + emisor_d.name + '</RznSoc>'
        xml_picking += '<GiroEmis>' + emisor_d.giro + '</GiroEmis>'
        xml_picking += '<Acteco>' + str(xml_data.company_id.acteco) + '</Acteco>' #Codigo de actividad emisor #Datos de prueba
        xml_picking += '<DirOrigen>' + emisor_d.street + '</DirOrigen>'
        xml_picking += '<CmnaOrigen>' + emisor_d.state_id.name + '</CmnaOrigen>'
        xml_picking += '</Emisor>' + '<Receptor>'
        xml_picking += '<RUTRecep>' + invoice_object.validar_rut(xml_data.partner_id.vat) + '</RUTRecep>'
        xml_picking += '<RznSocRecep>' + xml_data.partner_id.name + '</RznSocRecep>'
        xml_picking += '<GiroRecep>' + xml_data.partner_id.giro + '</GiroRecep>'
        xml_picking += '<Contacto>' + xml_data.partner_id.email + '</Contacto>'
        xml_picking += '<DirRecep>' + xml_data.partner_id.street + '</DirRecep>'
        xml_picking += '<CmnaRecep>' + xml_data.partner_id.state_id.name + '</CmnaRecep>'
        xml_picking += '<CiudadRecep>' + xml_data.partner_id.state_id.name + '</CiudadRecep>'
        xml_picking += '</Receptor>' + '<Totales>'            
        
        MntNeto = self.get_amount_untaxed(xml_data)
        xml_picking += '<MntNeto>'+ str(MntNeto) +'</MntNeto>'

        tax  = picking_obj.validar_iva(cr, uid, xml_data)
        xml_picking += self.validar_tax_in_xml(tax, MntNeto)
        xml_picking, i, product_te = self.validate_detail(xml_data, xml_picking)
        xml_picking += '<Referencia>'            
        xml_picking +='<NroLinRef>1</NroLinRef>'
        xml_picking +='<TpoDocRef>'+ str(xml_data.stock_journal_id.code_sii) +'</TpoDocRef>'
        xml_picking +='<FolioRef>'+ invoice_object.limpiar_campo_slash(xml_data.name) + '</FolioRef>'
        xml_picking +='<FchRef>'+ str(datetime.datetime.now().strftime("%Y-%m-%d")) +'</FchRef>'
        if xml_data.razonref:
            xml_picking +='<RazonRef>'+ xml_data.razonref +'</RazonRef>'
        xml_picking += '</Referencia>'            
        xml_picking += '</Documento>'
        xml_picking += '</DTE>'
        xml_picking.encode('ISO-8859-1')
        return xml_picking        

    def validate_detail(self, xml_data, xml_picking):
        invoice_object = self.pool.get('account.invoice')
        i = 1
        for record in xml_data.move_lines: 
            invoice_object.validar_campos_producto(record.product_id)
            xml_picking += '<Detalle>'
            xml_picking += '<NroLinDet>' + str(i) + '</NroLinDet>' + '<CdgItem>'
            xml_picking += '<TpoCodigo>' + record.product_id.cpcs_id.name + '</TpoCodigo>'
            xml_picking += '<VlrCodigo>' + invoice_object.limpiar_campo_guion(record.product_id.default_code) + '</VlrCodigo>' + '</CdgItem>'
            xml_picking += '<NmbItem>' + record.product_id.name + '</NmbItem>'
            xml_picking += '<DscItem>' + str(0) + '</DscItem>'                
            xml_picking += '<QtyItem>' + str(int(record.product_qty)) + '</QtyItem>'

            if record.product_id.uom_id:
                if len(record.product_id.uom_id.name) > 4:
                    unidad = record.product_id.uom_id.name[:4]                                              
#                    raise openerp.exceptions.Warning('Unidad de medida demasiado larga max 4 digitos: %s-%s' % (record.product_id.name,record.product_id.uom_id.name))
                else:
                    unidad = record.product_id.uom_id.name                        
            else:
                raise openerp.exceptions.Warning('Favor Ingresar Unidad de Medida para producto : %s' % record.product_id.name)                    
            xml_picking += '<UnmdRef>' + unidad + '</UnmdRef>'                
            xml_picking += '<PrcItem>' + str( int( record.product_id.list_price ) ) + '</PrcItem>'
            xml_picking += '<MontoItem>' + str( int(record.product_qty) *  int( record.product_id.list_price ) ) + '</MontoItem>'
            xml_picking += '</Detalle>'            
            if i == 1:
                product_te = record.product_id.name
            i += 1
        return xml_picking, i , product_te

    def get_amount_untaxed(self, xml_data):
        MntNeto = 0 
        for x in xml_data.move_lines:
            MntNeto += int(x.product_qty) *  int( x.product_id.list_price )             
        return MntNeto 
    
    def validar_tax_in_xml(self, tax, MntNeto):
        xml_picking = ''
        if tax:
            xml_picking += '<TasaIVA>'+ str( int(tax['amount']*100) ) +'</TasaIVA>'
            xml_picking += '<IVA>'+ str( int( MntNeto * tax['amount'] ) ) +'</IVA>'
            xml_picking += '<MntTotal>' + str( int( MntNeto * ( 1 + tax['amount']) )) + '</MntTotal>'
            xml_picking += '</Totales>' + '</Encabezado>'
        else:
            xml_picking += '<TasaIVA>'+ str(0) +'</TasaIVA>'
            xml_picking += '<IVA>'+ str(0) +'</IVA>'
            xml_picking += '<MntTotal>' + str( MntNeto ) + '</MntTotal>'
            xml_picking += '</Totales>' + '</Encabezado>'
        return xml_picking

    def xml_create(self, cr, uid, ids, context = None):
        picking_obj = self.pool.get('stock.picking')
        invoice_object = self.pool.get('account.invoice')
        xml_data = self.browse(cr, uid, ids)[0]
        if xml_data.stock_journal_id.code_sii:
            xml_picking = self.crear_dte(cr, uid, ids, context)
            par_firmador = invoice_object.validar_parametros_firmador(cr, uid)
            invoice_object.validar_parametros_certificado(cr, uid, xml_data.company_id)
            par_caf = invoice_object.validar_parametros_caf(cr, uid, xml_data.stock_journal_id.code_sii)
            file_name = invoice_object.limpiar_campo_slash(xml_data.name)
            file_name += '_'+datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            path = invoice_object.crear_archivo(xml_picking, file_name+'.xml')                        
            try:                 
                data = picking_obj.firmado_envio(cr, uid, xml_data, path, par_caf, par_firmador, 'stock.picking.out')                                                                     
            except:
                try:
                    os.remove(path)
                except:
                    print 'no hay archivo'
                raise openerp.exceptions.Warning('Error al crear DTE, Fallo en libreria facturisa')
        return True

stock_picking_out()