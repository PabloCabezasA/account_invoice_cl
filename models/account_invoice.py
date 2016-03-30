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
import openerp.exceptions
from lxml import etree
import xml.etree.ElementTree as ET
import datetime
from datetime import date
import time
import base64 , os
from elaphe import barcode
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email import encoders
import unicodedata
import json
import logging
_logger = logging.getLogger(__name__)

#Generador de XML y envio de factura electronica
class account_invoice(osv.osv):
    HEADERS= {'Content-type': 'application/json', 'Accept': 'text/plain'}

    URL = 'http://127.0.0.1:8080/'
    SEND_URL = URL + 'firmar_sii'
    TED_URL = URL + 'firmar_cliente'
    SEND_ORDER = URL + 'firmar_boleta'
    SEND_DIARY_URL = URL + 'firmar_reporte_consumo_folios'
    SEND_BOOK = URL + 'firmar_libro'
    
    _inherit = 'account.invoice'
    _columns = {
                'te_factura': fields.binary('te_factura'), 
                'factura_firmada': fields.binary('factura_firmada'),
                'xml_file': fields.binary('factura_firmada'), 
                'nombre_factura': fields.char('nombre_factura', size=200), 
                'export_filename': fields.char('factura XML', size=200),
                'trackid' : fields.char('trackid', size=200),
                'id_documento' : fields.char('Documento Unico', size=200),
                'razonref' : fields.char('razon ref', size=200),
                'state_emitidos': fields.one2many('account.invoice.emitidos','invoice','Facturacion SII', readonly=True),                
    }

    def print_pdf47(self,cr,uid,ids,context=None):
        invoice_obj = self.pool.get('account.invoice')
        xml_data = invoice_obj.browse(cr, uid, ids)[0]        
        xml_factura = self.crear_dte(cr, uid, ids)
        par_firmador = self.validar_parametros_firmador(cr, uid)
        self.validar_parametros_certificado(cr, uid, xml_data.company_id)
        par_caf = self.validar_parametros_caf(cr, uid, xml_data.journal_id.code_sii)
        file_name = self.limpiar_campo_slash(xml_data.number)                        
        path = self.crear_archivo(xml_factura, file_name+'.xml')                        
        data = self._info_for_facturador(cr, uid, xml_data, par_caf, par_firmador, path, 'account.invoice')        
        try:
            ted = self.pool.get('firmador.firmador').fimar_cliente(cr, uid, [xml_data.id], data, context=None)        
        except:            
            os.remove(path)
        os.remove(path)            
        self.funcion_pdf47(cr, uid, ids, ted['respuesta'])

    def print_for_idiots(self,cr,uid,ids,context=None):
        journal_id = False
        if not context:
            context = {}

        if ids:
            invoice = self.browse(cr, uid, ids[0], context)
        else:raise openerp.exceptions.Warning('Error al imprimir, Primero Guardar Factura')

        
        if context.has_key('journal_id'):
            journal_id = context['journal_id']
            journal_obj = self.pool.get('account.journal').browse(cr,uid,journal_id)
        
        if journal_id:            
            journal_obj.name
            datas = {
             'ids': ids,
             'model': 'account.invoice',             
             }            
            if journal_obj.type_print =='2':                
                if not invoice.te_factura:
                    self.print_pdf47(cr, uid, ids, context)

                return {
                        'type': 'ir.actions.report.xml',
                        'report_name': 'factura_elect',
                        'datas': datas,
                        'nodestroy' : True
                        }
            elif journal_obj.type_print =='1':    
                return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'account.invoice',
                    'datas': datas,
                    'nodestroy' : True
                }                        
            elif journal_obj.type_print =='3':
                if not invoice.te_factura:
                    self.print_pdf47(cr, uid, ids, context)
                return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'factura_elec_t',
                    'datas': datas,
                    'nodestroy' : True
                }
            elif journal_obj.type_print =='4':
                if not invoice.te_factura:
                    self.print_pdf47(cr, uid, ids, context)
                return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'factura_elec_n_t',
                    'datas': datas,
                    'nodestroy' : True
                }
	    
            raise openerp.exceptions.Warning('Error al imprimir, Agregar Tipo de Impresion a Diario')
        else : 
            raise openerp.exceptions.Warning('Error al imprimir, no se encuentra diario')
        

    def validar_parametros_firmador(self, cr, uid):
        context = {}
        acf_obj = self.pool.get('account.config.firma')
        for acf in acf_obj.browse(cr, uid, acf_obj.search(cr, uid, [], context)):
            return acf
        raise openerp.exceptions.Warning('Error al crear xml. Favor crear parametros del firmador')


    def validar_parametros_caf(self, cr, uid, code_sii):
        context = {}
        caf_obj = self.pool.get('account.invoice.folios')
        for caf in caf_obj.browse(cr, uid, caf_obj.search(cr, uid, [('code_sii','=', code_sii),('state_folio','=', '2')], limit=1, context=context)):
            return caf
        raise openerp.exceptions.Warning('Error al crear xml. Favor crear CAF')


    def validar_parametros_certificado(self, cr, uid, company):
        if not company.acteco:
            raise openerp.exceptions.Warning('Error al crear xml. Favor crear parametros acteco de compania')
        elif not company.filep12:
            raise openerp.exceptions.Warning('Error al crear xml. Favor crear parametros certificado de compania')
        elif not company.export_filename:
            raise openerp.exceptions.Warning('Error al crear xml. Favor crear parametros nombre certificado de compania')
        elif not company.nroresolucion:
            raise openerp.exceptions.Warning('Error al crear xml. Favor crear parametros Numero de resolucion de compania')
        elif not company.fecharesolucion:
            raise openerp.exceptions.Warning('Error al crear xml. Favor crear parametros Fecha de resolucion de compania')
#        elif not company.p12pass:
#            raise openerp.exceptions.Warning('Error al crear la factura. Favor crear parametros password p12 de compania')

    def crear_dte(self, cr, uid, ids):
        invoice_obj = self.pool.get('account.invoice')
        xml_data = invoice_obj.browse(cr, uid, ids)[0]        
        emisor_d = self.pool.get('res.partner').browse(cr, uid, xml_data.company_id.partner_id.id,)
        emisor_d = self.limpiar_campos_emisor_xml(cr, uid, emisor_d)
        self.limpiar_campos_receptor_xml(xml_data.partner_id)
        xml_factura = '<DTE version="1.0">'
        xml_factura += '<Documento ID="'+ xml_data.id_documento +'">' #Identificador único del DTE #Datos de Prueba            
        xml_factura += '<Encabezado>' + '<IdDoc>'        
        xml_factura += '<TipoDTE>' + xml_data.journal_id.code_sii + '</TipoDTE>' #Dato de prueba
        xml_factura += '<Folio>' + self.limpiar_campo_slash(xml_data.number) + '</Folio>' #Dato de prueba deveria estar en el rango de folios
        xml_factura += '<FchEmis>' + xml_data.date_invoice + '</FchEmis>'
        if xml_data.payment_term.name == None:
            raise openerp.exceptions.Warning('Favor Ingresar Plazo de Pago')
        else:
            if xml_data.payment_term.name.lower() == 'immediate payment':
                forma_pago = '1'
            else:
                forma_pago = '2'
        xml_factura += '<FmaPago>' + forma_pago + '</FmaPago>'
        xml_factura += '<FchVenc>' + xml_data.date_due + '</FchVenc>'
        xml_factura += '</IdDoc>' + '<Emisor>'
        xml_factura += '<RUTEmisor>'+self.validar_rut(xml_data.company_id.vat)+'</RUTEmisor>' #self.validar_rut(emisor_d['vat'])
        xml_factura += '<RznSoc>' + emisor_d.name + '</RznSoc>'
        xml_factura += '<GiroEmis>' + emisor_d.giro + '</GiroEmis>'
        xml_factura += '<Acteco>' + str(xml_data.company_id.acteco) + '</Acteco>' #Codigo de actividad emisor #Datos de prueba
        xml_factura += '<DirOrigen>' + emisor_d.street + '</DirOrigen>'
        xml_factura += '<CmnaOrigen>' + emisor_d.state_id.name + '</CmnaOrigen>'
        xml_factura += '<CdgVendedor>' + str(xml_data.user_id.id) + '</CdgVendedor>'            
        xml_factura += '</Emisor>' + '<Receptor>'
        xml_factura += '<RUTRecep>' + self.validar_rut(xml_data.partner_id.vat) + '</RUTRecep>'
        xml_factura += '<RznSocRecep>' + xml_data.partner_id.name + '</RznSocRecep>'
        xml_factura += '<GiroRecep>' + xml_data.partner_id.giro + '</GiroRecep>'
        xml_factura += '<Contacto>' + xml_data.partner_id.email + '</Contacto>'
        xml_factura += '<DirRecep>' + xml_data.partner_id.street + '</DirRecep>'
        xml_factura += '<CmnaRecep>' + xml_data.partner_id.state_id.name + '</CmnaRecep>'
        xml_factura += '<CiudadRecep>' + xml_data.partner_id.state_id.name + '</CiudadRecep>'
        impuesto_obj = self.buscar_impuesto_en_factura(cr, uid, xml_data, False)                        
        xml_factura += '</Receptor>' + '<Totales>'            
        xml_factura += '<MntNeto>' + str(int(xml_data.amount_untaxed)) + '</MntNeto>'                                
        xml_factura += '<MntExe>' + str(int(self.validar_total_exento(cr,uid,xml_data))) + '</MntExe>'            
        if impuesto_obj:
            xml_factura += '<TasaIVA>' + "{0:.2f}".format(impuesto_obj.amount * 100) + '</TasaIVA>'
        else:
            xml_factura += '<TasaIVA>'+'0'+'</TasaIVA>'
        xml_factura += '<IVA>' + str(int(xml_data.amount_tax)) + '</IVA>'
        xml_factura += '<MntTotal>' + str(int(xml_data.amount_total)) + '</MntTotal>'
        xml_factura += '</Totales>' + '</Encabezado>'

        i = 1
        for record in xml_data.invoice_line: 
            self.validar_campos_producto(record.product_id)
            xml_factura += '<Detalle>'
            xml_factura += '<NroLinDet>' + str(i) + '</NroLinDet>' + '<CdgItem>'
            xml_factura += '<TpoCodigo>' + record.product_id.cpcs_id.name + '</TpoCodigo>'
            xml_factura += '<VlrCodigo>' + self.limpiar_campo_guion(record.product_id.default_code) + '</VlrCodigo>' + '</CdgItem>'
            xml_factura += '<NmbItem>' + record.product_id.name + '</NmbItem>'
            xml_factura += '<DscItem>' + str(int(record.discount if record.discount else 0 )) + '</DscItem>'                
            if record.product_id.uom_id:
                if len(record.product_id.uom_id.name) > 4:
                     unidad = record.product_id.uom_id.name[:4]                                              
#                        raise openerp.exceptions.Warning('Unidad de medida demasiado larga max 4 digitos: %s-%s' % (record.product_id.uom_id.name,record.product_id.uom_id.name))
                else:
                    unidad = record.product_id.uom_id.name                        
            else:
                raise openerp.exceptions.Warning('Favor Ingresar Unidad de Medida para producto : %s' % record.product_id.uom_id.name)                    
            xml_factura += '<UnmdRef>' + unidad + '</UnmdRef>'                
            xml_factura += '<QtyItem>' + str(int(record.quantity)) + '</QtyItem>'
            xml_factura += '<PrcItem>' + str(int(record.price_unit)) + '</PrcItem>'
            xml_factura += '<MontoItem>' + str(int(record.price_subtotal * (impuesto_obj.amount +1)if record.invoice_line_tax_id else int(record.price_subtotal))) + '</MontoItem>'
            xml_factura += '</Detalle>'            
            if i == 1:
                product_te = record.product_id.name
            i += 1
        xml_factura += '<Referencia>'            
        xml_factura +='<NroLinRef>1</NroLinRef>'
        xml_factura +='<TpoDocRef>' + str(xml_data.journal_id.code_sii) + '</TpoDocRef>'
        xml_factura +='<FolioRef>'+ self.limpiar_campo_slash(xml_data.number) + '</FolioRef>'
        xml_factura +='<FchRef>'+ str(datetime.datetime.now().strftime("%Y-%m-%d")) +'</FchRef>'
        if xml_data.razonref:
            xml_factura +='<RazonRef>'+ xml_data.razonref +'</RazonRef>'
        xml_factura += '</Referencia>'            
        xml_factura += '</Documento>'
        xml_factura += '</DTE>'
        xml_factura.encode('ISO-8859-1')
        return xml_factura
    
    def xml_create(self, cr, uid, ids):
        invoice_obj = self.pool.get('account.invoice')
        xml_data = invoice_obj.browse(cr, uid, ids)[0]        
        if xml_data.journal_id.code_sii:            
            xml_factura = self.crear_dte(cr, uid, ids)
            par_firmador = self.validar_parametros_firmador(cr, uid)
            self.validar_parametros_certificado(cr, uid, xml_data.company_id)
            par_caf = self.validar_parametros_caf(cr, uid, xml_data.journal_id.code_sii)
            file_name = self.limpiar_campo_slash(xml_data.number)                        
            path = self.crear_archivo(xml_factura, file_name+'.xml')                        
            try:
                data = self.firmado_envio(cr, uid, xml_data, path, par_caf, par_firmador)                                                                     
            except:
                try:
                    os.remove(path)
                except:
                    print 'no hay archivo'
                raise openerp.exceptions.Warning('Error al crear DTE, Fallo en libreria facturisa')
            pathfirma = False
            if par_firmador.type_send== 'firmar':
                pathfirma = data['pathbase'] + '/out/dte_otros/xmlfiroc' + self.validar_rut(xml_data.company_id.vat).replace('-','') + str(xml_data.journal_id.code_sii) + str(self.limpiar_campo_slash(xml_data.number)) + '.xml'
            elif par_firmador.type_send== 'firmar_enviar':
                pathfirma = data['pathbase'] + '/out/dte_sii/xmlfirsii' + self.validar_rut(xml_data.company_id.vat).replace('-','') + str(xml_data.journal_id.code_sii) + str(self.limpiar_campo_slash(xml_data.number)) + '.xml'
            if pathfirma:
                self.enviar_correos(pathfirma, xml_data.partner_id, xml_data)                                    
        return True

    def special(self,valor):
        if valor == None:
            return ''
        return str(unicodedata.normalize('NFKD', valor).encode('ascii','ignore'))

    def firmado_envio(self, cr, uid, invoice, path, par_caf, par_firmador):
        data = self._info_for_facturador(cr, uid, invoice, par_caf, par_firmador, path, 'account.invoice')        
        if par_firmador.type_send == 'firmar_enviar':
            self.pool.get('firmador.firmador').firmar_enviar_sii(cr, uid, [invoice.id], data, context=None)
        elif par_firmador.type_send == 'firmar':
            self.pool.get('firmador.firmador').fimar_cliente(cr, uid, [invoice.id], data, context=None)
        else:
            raise openerp.exceptions.Warning('Error al crear xml. Favor ingrasar campo tipo de envio en Firmador')
        return data

    
    def _info_for_facturador(self, cr, uid, invoice, par_caf, par_firmador, path, objeto):
        data = {
                'document_id' : invoice.id,
                'rutaxmldte': path,
                'rutacertpfx': par_firmador.pathcertificado + invoice.company_id.export_filename,
                'contcertpxpfx': invoice.company_id.p12pass if invoice.company_id.p12pass else '', 
                'rutacaf':  par_firmador.pathfolio + par_caf.export_filename,
                'fecharesolucion': str(invoice.company_id.fecharesolucion), 
                'nroresolucion': str(invoice.company_id.nroresolucion), 
                'rutenvio': self.validar_rut(invoice.company_id.vat), 
                'pathbase': par_firmador.pathbase, 
                'modelo' : objeto,
                }
        _logger.info('Enviando al Facturador Estos datos %s' % data)
        return data
    
    def funcion_pdf47(self,cr,uid,ids,te_factura):
        path = os.getcwd() + '/openerp/v7/addons_econube/account_invoice_cl/%s'
        barcode('pdf417', te_factura, options=dict(eclevel=5, columns=15, rows=15), scale=2, data_mode='8bits').save(path % 'te_factura.png')
        with open(path % 'te_factura.png', "rb") as image_file:
            binary = base64.b64encode(image_file.read())
            self.pool.get('account.invoice').write(cr, uid, ids,{'te_factura': binary})
            os.remove(path % 'te_factura.png')

    
    def guardar_xml_factura(self,cr,uid,ids,xml):
        self.write(cr, uid, ids[0], {'xml_firmada':base64.encodestring(xml) ,'xml_factura':'DTE.xml'}, context=None)
        return True
    
    
    def validar_campos_producto(self, product_d):
        if not product_d.cpcs_id:
            raise openerp.exceptions.Warning('Error al crear xml. Favor ingrasar campo tipo de producto en producto %s ' % self.special(product_d['name']))
        if not  product_d.default_code:                
            raise openerp.exceptions.Warning('Error al crear xml. Favor ingrasar campo codigo(default_code) en producto %s ' % self.special(product_d['name']))
        
             
    def limpiar_campos_emisor_xml(self,cr,uid, emisor):        
        if not  emisor.vat:                
            raise openerp.exceptions.Warning('Error al crear xml. Favor ingrasar campo rut en partner de company')            
        if not emisor.name:
            raise openerp.exceptions.Warning('Error al crear xml. Favor ingrasar campo nombre en partner de company')        
        if not emisor.giro:
            raise openerp.exceptions.Warning('Error al crear xml. Favor ingrasar campo giro en partner de company')            
        if not emisor.street:
            raise openerp.exceptions.Warning('Error al crear xml. Favor ingrasar campo direccion en partner de company')        
        if not emisor.state_id:
            raise openerp.exceptions.Warning('Error al crear xml. Favor ingrasar campo Estado en partner de company')
        return emisor

    def limpiar_campos_receptor_xml(self, receptor):                        
        if not  receptor.vat:                
            raise openerp.exceptions.Warning('Error al crear xml. Favor ingrasar campo rut proveedor i/o cliente')            
        if not receptor.name:
            raise openerp.exceptions.Warning('Error al crear xml. Favor ingrasar campo nombre proveedor i/o cliente')        
        if not receptor.giro:
            raise openerp.exceptions.Warning('Error al crear xml. Favor ingrasar campo giro proveedor i/o cliente')            
        if not receptor.street:
            raise openerp.exceptions.Warning('Error al crear xml. Favor ingrasar campo direccion proveedor i/o cliente')        
        if not receptor.email:
            raise openerp.exceptions.Warning('Error al crear xml. Favor ingrasar campo correo proveedor i/o cliente')        
        if not receptor.state_id:
            raise openerp.exceptions.Warning('Error al crear xml. Favor ingrasar campo Estado proveedor i/o cliente')         

    
    def limpiar_campo_slash(self,numero):
        while str(numero).find('/') >= 0:
            position =0
            position = str(numero).find('/')
            numero = numero[position+1:]                    
        return numero
        
    def limpiar_campo_guion(self,numero):
        while str(numero).find('-') >= 0:
            position =0
            position = str(numero).find('-')
            numero = numero[position+1:]            
        return numero

    def validar_rut(self,rut):
        vat = ""
        cont = 0
        if len(rut) > 0 :
            for r in rut:
                cont += 1
                if not r.isalpha() and not r == '.' and not r == '-':   
                    vat +=r
                elif cont == len(rut):
                    vat +=r
        return str(str(vat[:len(vat)-1])+'-'+vat[len(vat)-1]).strip()


    def enviar_correos(self, pathfirma , partner, data):                                                                                                                                                                                                                                                
        msg = MIMEMultipart()
        destinatario = ['%s <%s>' % (partner.name,partner.email) ] 
        msg['To'] = '%s' % partner.email
        msg['From'] = 'dte@econube.cl'        
        msg['Subject'] = 'factura numero %s' % str(data.number)                    
        name_file = 'DTE_PRUEBA_%s.xml'  % str(datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S"))
        msg.attach(MIMEText("""
        Estimado cliente adjunto factura N°<h3>%s</h3></br>
        sub total: %s</br>
        impuesto: %s</br>
        total: %s</br>"""%(str(data.number),str(data.amount_untaxed),str(data.amount_tax),str(data.amount_total))
        ,'html'))                
        adjunto = MIMEBase('multipart', 'mixed')                
        with open(pathfirma, 'r') as myfile:
            adjunto.set_payload(myfile.read())
            print adjunto
            myfile.close()        
        encoders.encode_base64(adjunto)        
        adjunto.add_header('Content-Disposition', 'attachment', filename='factura.xml')        
        msg.attach(adjunto)                
        mailServer = smtplib.SMTP('mail.econube.cl', 26)        
        mailServer.set_debuglevel(1)
        mailServer.ehlo()
        mailServer.starttls()                        
        mailServer.login("dte@econube.cl","dte2015")
        mailServer.sendmail("dte@econube.cl", destinatario, msg.as_string())
        mailServer.quit()

    
    def crear_archivo(self, xml, name_file):
        path = '/tmp/'+name_file
        archi=open(path,'a+b')
        archi.write(self.special(xml))                                
        archi.close()
        return path


    def buscar_impuesto_en_factura(self,cr,uid,invoice_id,context=None):                
        tax_id = []
        for line in invoice_id.invoice_line:
            for tax in line.invoice_line_tax_id:
                if not tax_id:
                    tax_id.append(tax.id)
                elif tax.id not in tax_id:                    
                    raise osv.except_osv('Distintos Impuestos!',"Solo puede haber un tipo de impuesto por factura" )
        if tax_id:
            return self.pool.get('account.tax').browse(cr,uid,tax_id[0])
        else:return False
        

    def validar_total_exento(self,cr,uid,invoice_id,context=None):                
        total = 0
        for line in invoice_id.invoice_line:
            if  line.invoice_line_tax_id:
                continue
            else:
                total+= line.price_subtotal
        return total

account_invoice()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:#