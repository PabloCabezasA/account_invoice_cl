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

from openerp import  models, fields, api
from openerp.osv import osv
from xml.dom.minidom import parse
from datetime import datetime
import base64
import unicodedata
import os

class account_config_firma(models.Model):
    _name='account.config.firma'
    pathbase = fields.Char("Path base", help='Ruta a la libreria ej: /home/openerp/lfubu14_64', size=250)
    pathfolio = fields.Char("Path folios", help='Ruta a los folios ej: /home/openerp/caf/', size=250)
    pathcertificado = fields.Char("Path Certificados", help='Ruta a los certificados ej: /home/openerp/certificados/', size=250)             
    type_send = fields.Selection([
               ('firmar','Firmar'),
               ('firmar_enviar','Firmado e envio'), 
               ], 'Tipo de Envio')
    

account_config_firma()


class siiSetDte(osv.osv_memory):
    _name='sii.set.dte'
    name = fields.Char("Nombre", size=250)
    qty = fields.Integer("Documentos", size=250)
    xml_file = fields.Binary('Set de Prueba')
    xml_name = fields.Char('Nombre xml', size=200)
    company_id = fields.Many2one('res.company', 'Compañia')
    partner_id = fields.Many2one('res.partner', 'Proveedor') 

    @api.one
    def enviar_archivo_set(self):        
        if self.xml_file:
            par_firmador = self.env['account.invoice'].validar_parametros_firmador()
            path = '/tmp/sendSetPrueba_' + self.xml_name
            vfile = open(path,'a+b')
            vfile.write( base64.decodestring(self.xml_file))
            vfile.close()
            data ={ 'path' : path,
                    'cert': par_firmador.pathcertificado + self.company_id.export_filename, 
                    'passwd' :self.company_id.p12pass if self.company_id.p12pass else '',
                    'name' : par_firmador.pathbase + '/out/resp_sii/resp_SetPrueba' + self.xml_name, 
                    'pathbase' : par_firmador.pathbase
                    }
            self.env['firmador.firmador'].enviar_libro_sii(data)
        else:
            raise Warning('Error al enviar xml. Favor primero generar el Libro') 
    
    @api.multi
    def crear_archivo_set(self):
        self.env.cr.execute("""
            select id from account_invoice where to_setest = True and state not in('draft', 'cancel')
            and company_id = %d and partner_id = %d and type in ('out_invoice','out_refund') 
        """ %  (self.company_id.id, self.partner_id.id) )
        all_ids = map(lambda x:x[0], self.env.cr.fetchall())
        if not all_ids:
            raise Warning('Error, No se encontraron ducumentos')
        invoice_obj = self.env['account.invoice']
        par_firmador = self.env['account.invoice'].validar_parametros_firmador()
        pathbase = par_firmador.pathbase
        dataxml_dict = {}
        for invoice in invoice_obj.browse(all_ids):
            if not invoice.export_filename:
                continue
            xml_data, type = self.buscar_archivo_xml(invoice.export_filename , pathbase)
            if not xml_data:
                continue
            if type not in dataxml_dict.keys(): 
                dataxml_dict[type] = []
            dataxml_dict[type].append(xml_data)
        if not dataxml_dict:
            raise Warning('Error, Compruebe las rutas y archivos firmados')
        
        path, xml = self.crear_xml_setprueba(dataxml_dict)        
        try:
            cert = par_firmador.pathcertificado + self.company_id.export_filename                
            data = {'path': path, 'cert': cert, 'passwd': self.company_id.p12pass, 'pathbase':par_firmador.pathbase}        
            set_xml = self.env['firmador.firmador'].firmar_set_prueba_sii(data)
            self.open_file_and_write(set_xml)
            self.qty_total(dataxml_dict)
            os.remove(path)
        except:
            os.remove(path)
        mod_obj = self.env['ir.model.data']
        res = mod_obj.get_object_reference('account_invoice_cl', 'conf_siisetdte_form')                                           
        return {
            'name': 'sii.set.dte.form',
            'context': self._context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sii.set.dte',
            'type': 'ir.actions.act_window',
            'views': [(res[1], 'form')],
            'res_id': self.id,
            'target': 'new',             
        }
    
    @api.model
    def open_file_and_write(self, set_xml):
        encoded = ''        
        with open(set_xml, 'r') as myfile:
            encoded = base64.b64encode(myfile.read())
            myfile.close()
        self.write({'xml_file': encoded, 'xml_name': 'SET_%s.xml' % str( datetime.now().strftime('%Y-%m-%d') ) })
        os.remove(set_xml)
 
    @api.model
    def qty_total(self, datal):
        qty = 0
        for key in datal.keys():
            qty += len(datal[key])
        self.write({'qty': qty})
        
    @api.model
    def crear_xml_setprueba(self, dataxml_dict):
        xml = '<?xml version="1.0" encoding="ISO-8859-1"?>'
        xml += '<EnvioDTE xmlns="http://www.sii.cl/SiiDte" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.0" xsi:schemaLocation="http://www.sii.cl/SiiDte EnvioDTE_v10.xsd">'
        xml += '<SetDTE ID="SetDoc">'
        xml += '<Caratula version="1.0">'
        xml += '<RutEmisor>'+ self.validar_rut(self.company_id.vat)+'</RutEmisor>'
        xml += '<RutEnvia>'+ self.validar_rut(self.company_id.rutenvia)+'</RutEnvia>'
        xml += '<RutReceptor>'+ self.validar_rut(self.partner_id.vat)+'</RutReceptor>'
        xml += '<FchResol>'+ self.company_id.fecharesolucion +'</FchResol>'
        xml += '<NroResol>0</NroResol>'
        xml += '<TmstFirmaEnv>'+ str( datetime.now().strftime('%Y-%m-%dT%H:%M:%S') ) +'</TmstFirmaEnv>'
        for key in dataxml_dict.keys():            
            xml += '<SubTotDTE>'
            xml += '<TpoDTE>'+str(key)+'</TpoDTE>'
            xml += '<NroDTE>'+ str(len(dataxml_dict[key])) +'</NroDTE>'
            xml += '</SubTotDTE>'        
        xml += '</Caratula>'
        for key in dataxml_dict.keys():            
            for data in dataxml_dict[key]:                
                xml += data        
        xml += '</SetDTE>'
        xml += '</EnvioDTE>'       
        path = self.create_file(xml)
        return path, xml
    
    @api.model
    def create_file(self, data):
        path =  '/tmp/%s.xml' % str( datetime.now().strftime('%Y-%m-%d') )
        file=open( path, 'a+b')
        file.write(self.special(data))                                
        file.close()
        return path

    @api.model
    def special(self,valor):
        if valor == None:
            return ''
        return str(unicodedata.normalize('NFKD', valor).encode('ascii','ignore'))

    @api.model            
    def buscar_archivo_xml(self, name_file, pathbase):    
        pathxmlfirmado = pathbase + '/out/dte_setprueba/'
        xmlfirmadosii = pathbase + '/out/dte_setprueba/'+ name_file
        xml_str = False
        type = False
        try:
            dom1 = parse(xmlfirmadosii)
            dte = dom1.getElementsByTagName('DTE')
            if dte:
                dte = dte[-1]
            xml_str = dte.toxml()
            type = dte.getElementsByTagName("TipoDTE")[0].childNodes[0].data
        except IOError as e:
            print "I/O error({0}): {1}".format(e.errno, e.strerror)
        return xml_str, type                

    @api.model
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

siiSetDte()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:#