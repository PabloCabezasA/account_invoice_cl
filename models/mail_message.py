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
import openerp.exceptions
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _
import smtplib
import email.utils
from email.mime.text import MIMEText                    
import base64
import xml.etree.ElementTree as ET 


class mail_alias(osv.Model):
    """
    Se remplasa la funcion _get_alias_domain para el campo alias_domain ya que por defecto openerp solo permite tener
    1 alias configurado,se le agregara al codigo una funcion que detecte cuando el usuario tenga
    el nombre de SII y se le asignara el alias de econube.cl, para que a el le lleguen los correos
    de facturacion electronica.
    """    
    _inherit = 'mail.alias'            
    _name = 'mail.alias'
    
    def _get_alias_domain(self, cr, uid, ids, name, args, context=None):
        #parte de codigo modificado
        user = self.browse (cr, uid, ids)[0]
        if user.alias_user_id.user_sii_mail == True:
            domain = 'econube.cl'
            return dict.fromkeys(ids, domain or "")
        #codigo original    
        ir_config_parameter = self.pool.get("ir.config_parameter")
        domain = ir_config_parameter.get_param(cr, uid, "mail.catchall.domain", context=context)
        return dict.fromkeys(ids, domain or "")

    _columns = {
                'alias_domain': fields.function(_get_alias_domain, string="Alias domain", type='char', size=None),
                }
mail_alias()


class mail_message(osv.osv):
    _inherit = "mail.message"    
    _name= "mail.message"
    #Acción servidor se ejecuta al encontrar mensages en el correo configurado    

    def mail_enter(self, cr, uid, object, context=None):            
        user_id_correo = self.buscar_partner_usuario_correo_sii( cr, uid , context)
        xml_dicts=False
        if user_id_correo is None: return True
        xml_dict = False                                
        message_id = self.buscar_notificaciones(cr, user_id_correo[0])
        if not message_id: return True
        mail_message = self.pool.get('mail.message')
        ir_attachment = self.pool.get('ir.attachment')                           
        messages = mail_message.read(cr, uid, message_id)
        for message in messages:
            #Leer archivos adjuntos para validar si es de SII            
            if len( message['attachment_ids'] ) >0:                
                adjuntos= ir_attachment.read(cr, uid, message['attachment_ids'] )
                for adj in adjuntos:                                                        
                    if adj['name'].endswith('.xml'):
                        try:                                                    
                            cr.execute('UPDATE mail_notification SET read = True where message_id = {0} and partner_id = {1} '.format(message['id'],user_id_correo[0]))                            
                            xml_dicts=self.buscar_datos_en_archivo_xml(cr, uid, adj['datas'])
                        except:                            
                            cr.execute('UPDATE mail_notification set read = Null where message_id = {0} and partner_id = {1}'.format(message['id'],user_id_correo[0]))
                    else:continue                                                                                                    
                    if xml_dicts:
			a = ""			
                        try:
		            a="buscar datos en basico"
                            open_dict,servicio_basico = self.buscar_datos_en_openerp_xml(cr, uid, xml_dicts)                        
                            if servicio_basico:
				a = 'crear factura'
                                if open_dict['TYPE']=='purchase':
                                    factura = self.crear_factura_recibida(cr, uid, open_dict, xml_dicts,'compra', context)
                                elif open_dict['TYPE']=='sale':
                                    factura = self.crear_factura_recibida(cr, uid, open_dict, xml_dicts,'venta', context)
                            else:
				a = "buscar factura partner"
                                self.buscar_factura_partner(cr, uid, open_dict, xml_dicts)                                                                                      
                        except:
			    raise openerp.exceptions.Warning('error en exepciona'+a)                            
                            continue                        
            
            
    #Esta funcion busca la factura a partir del proveedor, estado y el monto.    
    def buscar_factura_partner(self,cr,uid,dict,xml_dicts,context=None):                
        invoice_obj = self.pool.get('account.invoice')                
        invoice_dte_obj = self.pool.get('account.invoice.dte')
        actualizo = False
        id_factura = self.validar_factura_existente(cr,uid,xml_dicts,dict,invoice_obj)                        
        if id_factura:
            self.actualizar_factura_existente(cr,uid,id_factura[0],xml_dicts)
            actualizo = True                
        if dict['TYPE']=='purchase':        
            if id_factura:
                print "encontrado"
                self.crear_factura_recibida(cr, uid, dict, xml_dicts,'compra', context)
        elif dict['TYPE']=='sale':
            if id_factura:
                print "encontrado"
                self.crear_factura_recibida(cr, uid, dict, xml_dicts,'sale', context)


    def validar_factura_existente(self,cr,uid,xml_dicts,dict,invoice_obj):        
        max_amount_total = float(str("%d.99"% int(xml_dicts[6]['MntTotal'])))
        max_amount_untaxed = float(str("%d.99"% int(xml_dicts[6]['MntNeto'])))             
        cr.execute("""select id from account_invoice where journal_id ={0}
              and partner_id ={1} 
              and state ='draft' 
              and amount_total >= {2}
              and amount_total <= {3} 
              and amount_untaxed >= {4}
              and amount_untaxed <= {5}
        """.format(dict['DIARIO']['id'],dict['PROVEDOR'][0] if dict['PROVEDOR'] else dict['CLIENTE'][0] ,int(xml_dicts[6]['MntTotal']),max_amount_total,int(xml_dicts[6]['MntNeto']),max_amount_untaxed)
        )
        id_factura = cr.fetchone()
        if id_factura:
            return id_factura
        else:
            return False 


    def actualizar_factura_existente(self,cr,uid,id_factura,xml_dicts,context=None):
        vals = {'date_invoice':xml_dicts[2]['FchEmis'], 'date_due':xml_dicts[2]['FchVenc'], 'supplier_invoice_number':xml_dicts[2]['Folio'] }
        self.pool.get('account.invoice').write(cr,uid,id_factura,vals)


    def validar_factura_existente_dte(self, cr, uid, xml_dicts, dict, invoice_dte_obj):
        max_amount_total = float(str("%d.99"% int(xml_dicts[6]['MntTotal'])))
        max_amount_untaxed = float(str("%d.99"% int(xml_dicts[6]['MntNeto'])))
        id_factura = invoice_dte_obj.search(cr,uid,[
                                           ('journal_id','=', dict['DIARIO']['id']),
                                           ('partner_id','=', dict['PROVEDOR'][0] if dict['PROVEDOR'] else dict['CLIENTE'][0]),
                                           ('state','=', 'draft'),
                                           ('amount_total','>=',int(xml_dicts[6]['MntTotal']) ),('amount_total','<=',max_amount_total),
                                           ('amount_untaxed','>=',int(xml_dicts[6]['MntNeto']) ),('amount_total','<=',max_amount_untaxed),                                       
                                           ])
        return id_factura 

                            
    #la funcion retorna Identificador de Envio,Informados,Rechazos,Reparos,Aceptados    
    def buscar_datos_en_archivo_xml(self,cr,uid,datas):        
        xml = base64.decodestring(datas)
        tree = ET.fromstring(xml)                                             
        list_dicts = []
        xml_caratula = {'RutEmisor':False,'RutEnvia':False,'RutReceptor':False,
                        'FchResol': False,'NroResol':False                    
                    }
        #xml caratula
        caratula = tree.find('{http://www.sii.cl/SiiDte}SetDTE').find('{http://www.sii.cl/SiiDte}Caratula')
        RutEmisor = caratula.find('{http://www.sii.cl/SiiDte}RutEmisor')
        RutEnvia = caratula.find('{http://www.sii.cl/SiiDte}RutEnvia')
        RutReceptor = caratula.find('{http://www.sii.cl/SiiDte}RutReceptor')
        FchResol = caratula.find('{http://www.sii.cl/SiiDte}FchResol')
        NroResol = caratula.find('{http://www.sii.cl/SiiDte}NroResol')                        
        xml_caratula['RutEmisor'] = RutEmisor.text if RutEmisor != None else False
        xml_caratula['RutEnvia'] = RutEnvia.text if RutEnvia != None else False
        xml_caratula['RutReceptor'] = RutReceptor.text if RutReceptor != None else False
        xml_caratula['FchResol'] = FchResol.text if FchResol != None else False
        xml_caratula['NroResol'] = NroResol.text if NroResol != None else False        
        list_dicts.insert(0,xml_caratula)
        #xml SubTotDTE
        xml_DTE = {
                        'TpoDTE':False,'NroDTE':False                    
                        }
        
        SubTotDTE = caratula.find('{http://www.sii.cl/SiiDte}SubTotDTE')
        TpoDTE = SubTotDTE.find('{http://www.sii.cl/SiiDte}TpoDTE')                
        NroDTE = SubTotDTE.find('{http://www.sii.cl/SiiDte}NroDTE')
        
        xml_DTE['TpoDTE'] = TpoDTE.text if TpoDTE != None else False
        xml_DTE['NroDTE'] = NroDTE.text if NroDTE != None else False 
        list_dicts.insert(1,xml_DTE)
        #xml ENCABEZADO
        DTE = tree.find('{http://www.sii.cl/SiiDte}SetDTE').find('{http://www.sii.cl/SiiDte}DTE')
        Encabezado = DTE.find('{http://www.sii.cl/SiiDte}Documento').find('{http://www.sii.cl/SiiDte}Encabezado')
        #xml IdDoc
        xml_IdDoc = {'TipoDTE':False,'Folio':False,'FchEmis':False,
                        'IndServicio': False,'MntBruto':False,'TermPagoGlosa':False,
                        'FchVenc':False                    
                        }    
        IdDoc =  Encabezado.find('{http://www.sii.cl/SiiDte}IdDoc')        
        TipoDTE = IdDoc.find('{http://www.sii.cl/SiiDte}TipoDTE')
        Folio = IdDoc.find('{http://www.sii.cl/SiiDte}Folio')
        FchEmis = IdDoc.find('{http://www.sii.cl/SiiDte}FchEmis')
        IndServicio = IdDoc.find('{http://www.sii.cl/SiiDte}IndServicio')
        MntBruto = IdDoc.find('{http://www.sii.cl/SiiDte}MntBruto')
        TermPagoGlosa = IdDoc.find('{http://www.sii.cl/SiiDte}TermPagoGlosa')
        FchVenc = IdDoc.find('{http://www.sii.cl/SiiDte}FchVenc')
        xml_IdDoc['TipoDTE'] = TipoDTE.text if TipoDTE != None else False
        xml_IdDoc['Folio'] = Folio.text if Folio != None else False
        xml_IdDoc['FchEmis'] = FchEmis.text if FchEmis != None else False
        xml_IdDoc['IndServicio'] = IndServicio.text if IndServicio != None else False
        xml_IdDoc['MntBruto'] = MntBruto.text if MntBruto != None else False
        xml_IdDoc['TermPagoGlosa'] = TermPagoGlosa.text if TermPagoGlosa != None else False
        xml_IdDoc['FchVenc'] = FchVenc.text if FchVenc != None else False
        list_dicts.insert(2,xml_IdDoc)
        #xml Emisor
        xml_Emisor  = {'RUTEmisor':False,'RznSoc':False,'GiroEmis':False,
                        'Acteco': False,'DirOrigen':False,'CmnaOrigen':False
                        ,'CiudadOrigen':False                    
                        }        
        Emisor =  Encabezado.find('{http://www.sii.cl/SiiDte}Emisor')        
        RUTEmisor = Emisor.find('{http://www.sii.cl/SiiDte}RUTEmisor')
        RznSoc = Emisor.find('{http://www.sii.cl/SiiDte}RznSoc')
        GiroEmis = Emisor.find('{http://www.sii.cl/SiiDte}GiroEmis')
        Acteco = Emisor.find('{http://www.sii.cl/SiiDte}Acteco')
        DirOrigen = Emisor.find('{http://www.sii.cl/SiiDte}DirOrigen')
        CmnaOrigen = Emisor.find('{http://www.sii.cl/SiiDte}CmnaOrigen')
        CiudadOrigen = Emisor.find('{http://www.sii.cl/SiiDte}CiudadOrigen')
        xml_Emisor['RUTEmisor']= RUTEmisor.text if RUTEmisor != None else False
        xml_Emisor['RznSoc']= RznSoc.text if RznSoc != None else False
        xml_Emisor['GiroEmis']= GiroEmis.text if GiroEmis != None else False
        xml_Emisor['Acteco']= Acteco.text if Acteco != None else False
        xml_Emisor['DirOrigen']= DirOrigen.text if DirOrigen != None else False
        xml_Emisor['CmnaOrigen']= CmnaOrigen.text if CmnaOrigen != None else False
        xml_Emisor['CiudadOrigen']= CiudadOrigen.text if CiudadOrigen != None else False
        list_dicts.insert(3,xml_Emisor)
        #xml Receptor
        xml_Receptor  = {'RUTRecep':False,'CdgIntRecep':False,'RznSocRecep':False,
                        'GiroRecep': False,'Contacto':False,'CorreoRecep':False
                        ,'DirRecep':False,'CmnaRecep':False,'CiudadRecep':False,
                        'DirPostal':False,'CmnaPostal':False,'CiudadPostal':False                    
                        }
        Receptor =  Encabezado.find('{http://www.sii.cl/SiiDte}Receptor')        
        RUTRecep = Receptor.find('{http://www.sii.cl/SiiDte}RUTRecep')
        CdgIntRecep = Receptor.find('{http://www.sii.cl/SiiDte}CdgIntRecep')
        RznSocRecep = Receptor.find('{http://www.sii.cl/SiiDte}RznSocRecep')
        GiroRecep = Receptor.find('{http://www.sii.cl/SiiDte}GiroRecep')
        Contacto = Receptor.find('{http://www.sii.cl/SiiDte}Contacto')
        CorreoRecep = Receptor.find('{http://www.sii.cl/SiiDte}CorreoRecep')
        DirRecep = Receptor.find('{http://www.sii.cl/SiiDte}DirRecep')
        CmnaRecep = Receptor.find('{http://www.sii.cl/SiiDte}CmnaRecep')
        CiudadRecep = Receptor.find('{http://www.sii.cl/SiiDte}CiudadRecep')
        DirPostal = Receptor.find('{http://www.sii.cl/SiiDte}DirPostal')
        CmnaPostal = Receptor.find('{http://www.sii.cl/SiiDte}CmnaPostal')
        CiudadPostal = Receptor.find('{http://www.sii.cl/SiiDte}CiudadPostal')
        xml_Receptor['RUTRecep'] = RUTRecep.text if RUTRecep != None else False
        xml_Receptor['CdgIntRecep'] = CdgIntRecep.text if CdgIntRecep != None else False
        xml_Receptor['RznSocRecep'] = RznSocRecep.text if RznSocRecep != None else False
        xml_Receptor['GiroRecep'] = GiroRecep.text if GiroRecep != None else False
        xml_Receptor['Contacto'] = Contacto.text if Contacto != None else False
        xml_Receptor['CorreoRecep'] = CorreoRecep.text if CorreoRecep != None else False
        xml_Receptor['DirRecep'] = DirRecep.text if DirRecep != None else False
        xml_Receptor['CmnaRecep'] = CmnaRecep.text if CmnaRecep != None else False
        xml_Receptor['CiudadRecep'] = CiudadRecep.text if CiudadRecep != None else False
        xml_Receptor['DirPostal'] = DirPostal.text if DirPostal != None else False
        xml_Receptor['CmnaPostal'] = CmnaPostal.text if CmnaPostal != None else False
        xml_Receptor['CiudadPostal'] = CiudadPostal.text if CiudadPostal != None else False
        list_dicts.insert(4,xml_Receptor)
        #xml Transporte
        xml_Transporte  = {'DirDest':False,'CmnaDest':False,'CiudadDest':False}        
        Transporte =  Encabezado.find('{http://www.sii.cl/SiiDte}Transporte')          
        if Transporte != None:
            DirDest = Transporte.find('{http://www.sii.cl/SiiDte}DirDest')
            CmnaDest = Transporte.find('{http://www.sii.cl/SiiDte}CmnaDest')
            CiudadDest = Transporte.find('{http://www.sii.cl/SiiDte}CiudadDest')
            xml_Transporte['DirDest'] = DirDest.text if DirDest != None else False
            xml_Transporte['CmnaDest'] = CmnaDest.text if CmnaDest != None else False
            xml_Transporte['CiudadDest'] = CiudadDest.text if CiudadDest != None else False
        list_dicts.insert(5,xml_Transporte)
        #xml Totales
        xml_Totales  = {'MntNeto':False,'TasaIVA':False,'IVA':False,
                        'MntTotal': False,'MontoNF':False,'VlrPagar':False                                            
                        }
        Totales =  Encabezado.find('{http://www.sii.cl/SiiDte}Totales')          
        MntNeto = Totales.find('{http://www.sii.cl/SiiDte}MntNeto')
        TasaIVA = Totales.find('{http://www.sii.cl/SiiDte}TasaIVA')
        IVA = Totales.find('{http://www.sii.cl/SiiDte}IVA')
        MntTotal = Totales.find('{http://www.sii.cl/SiiDte}MntTotal')
        MontoNF = Totales.find('{http://www.sii.cl/SiiDte}MontoNF')
        VlrPagar = Totales.find('{http://www.sii.cl/SiiDte}VlrPagar')                                    
        
        xml_Totales['MntNeto'] = MntNeto.text if MntNeto != None else False
        xml_Totales['TasaIVA'] = TasaIVA.text if TasaIVA != None else False
        xml_Totales['IVA'] = IVA.text if IVA != None else False
        xml_Totales['MntTotal'] = MntTotal.text if MntTotal != None else False
        xml_Totales['MontoNF'] = MontoNF.text if MontoNF != None else False
        xml_Totales['VlrPagar'] = VlrPagar.text if VlrPagar != None else False
        list_dicts.insert(6,xml_Totales)
        
        Lineas = DTE.find('{http://www.sii.cl/SiiDte}Documento').findall('{http://www.sii.cl/SiiDte}Detalle')
        lines= []
        for linea in Lineas:
            xml_lineas  = {'NroLinDet':False,'IndExe':False,'NmbItem':False,'MontoItem':False,'QtyItem':False,'PrcItem':False}                        
            NroLinDet = linea.find('{http://www.sii.cl/SiiDte}NroLinDet')
            IndExe = linea.find('{http://www.sii.cl/SiiDte}IndExe')
            NmbItem = linea.find('{http://www.sii.cl/SiiDte}NmbItem')
            MontoItem = linea.find('{http://www.sii.cl/SiiDte}MontoItem')
            QtyItem = linea.find('{http://www.sii.cl/SiiDte}QtyItem')
            PrcItem = linea.find('{http://www.sii.cl/SiiDte}PrcItem')          
            xml_lineas['NroLinDet'] = NroLinDet.text if NroLinDet != None else False
            xml_lineas['IndExe'] = IndExe.text if IndExe != None else False
            xml_lineas['NmbItem'] = NmbItem.text if NmbItem != None else False
            xml_lineas['MontoItem'] = MontoItem.text if MontoItem != None else False
            xml_lineas['QtyItem'] = QtyItem.text if QtyItem != None else False
            xml_lineas['PrcItem'] = PrcItem.text if PrcItem != None else False
            lines.append(xml_lineas)                            
        list_dicts.insert(7,lines)
        return list_dicts
    
    
    #esta funcion retorna el tipo de diario segun sii y busca el proveedor o cliente
    #segun sea el caso    
    #Genaro Jorquera: cuandoe s proveedores debes viene un tag que se llama TD que es el tipo de documento, ese lo conviertes (pasando por la tabla de tipo documento SII) a diario y buscar en el invoice si existe un documento de ese tipo en estado borrador (creo que lo mejor solo el validar rut, docto en borardor y no tipo documento a nivel identico ej: si es factura (todos los tipo facturas) porque lo mas seguro que cuando se genera el borrador en open pongan factura normal y no electronica) para ese proveedor, si es asi, debes comparar el total si son =, si es asi se debe insertar al documento borrador
    #Genaro Jorquera: la fecha del documento, fecha vencimiento y numero documento
    #Genaro Jorquera: si no existe un documento en borrador debera insertarse en esa tabla invoice_dte y se debe generar una vista para que muestre o visualice esos documento y que permita editar y generar un boton para traspasar dichos documentos al invoice (eso pasara con todos las fact de servicios basicos (agua, telefono, electricidad), ya que en ellos no existe OC por ende no existira documentos en borrador        
    

    def buscar_datos_en_openerp_xml(self,cr,uid,data,context=None):
        account_journal_obj = self.pool.get('account.journal')
        acc_jourcl_obj = self.pool.get('account.journal')        
        open_dict = {'DIARIO':False,'PROVEDOR':False,'CLIENTE':False,'TYPE':False}                                                
        vat_partner = self.validar_rut(data[0]['RutEmisor'])
        vat_cliente = self.validar_rut(data[0]['RutEnvia'])
        partner_r = False
        servicio_basico = False
        #buscar diario segun codigo sii
        try:
            acc_jourcl_ids = acc_jourcl_obj.search(cr,uid,[('code_sii','=', data[1]['TpoDTE'])])
            acc_jourcl =  acc_jourcl_obj.read(cr,uid,acc_jourcl_ids)[0]
        except:
            return open_dict
        #buscar buscar provedor o cliente segun tipo de diario
        try:                                                
            open_dict['DIARIO'] = acc_jourcl                    
            id_partner = self.buscar_proveedor_cliente(cr, uid, vat_partner)
            
            if id_partner is None:
                #data[3] son datos del emisor
                id_partner = self.crear_partner(cr,uid,data[3],False,True)
                partner_r = [id_partner]         
            else:
                partner_r = id_partner
                servicio_basico = self.pool.get('res.partner').browse(cr,uid,id_partner[0]).servicio_basicos                             
            if acc_jourcl['type'] == 'purchase':                
                open_dict['TYPE'] = 'purchase'
                open_dict['PROVEDOR'] = partner_r
            elif acc_jourcl['type'] == 'sale':                
                open_dict['TYPE'] = 'sale'                                                                                 
                open_dict['CLIENTE'] = partner_r            
        except:
            return open_dict,servicio_basico        
        return open_dict,servicio_basico


    # esta funcion hace lo que dice el nombre de la funcion
    

    def crear_factura_recibida(self,cr,uid,dict,xml_dicts,type,context=None):
        invoice_dte = self.pool.get('account.invoice.dte')
        invoice_dte_line = self.pool.get('account.invoice.line.dte')
        res_partner = self.pool.get('res.partner').browse(cr, uid, dict['PROVEDOR'][0] if dict['PROVEDOR'] else dict['CLIENTE'][0])        
        vals = {'partner_id' : False,'reference_type' : 'none' , 'date_invoice' : False, 'date_due': False ,'account_id' : False ,'journal_id': False, 'currency_id' : False}        
        vals_line = {'name' : False,'account_id' : False , 'quantity' : 1.0, 'price_unit': False ,'invoice_line_tax_id' : [] }        
        account_id,default_account = self.buscar_cuentas_defecto_factDte(cr, type,res_partner)
        default_iva = self.buscar_iva_defecto_factDte(cr, type,res_partner)
        divisa = self.buscar_divisa(cr) 
        if type == 'compra':
           context ={ 'journal_type': 'purchase', 'default_type': 'in_invoice', 'type': 'in_invoice'}       
        try:
            vals['partner_id'] = dict['PROVEDOR'][0] if type == 'compra' else  dict['CLIENTE'][0]
            vals['journal_id'] = dict['DIARIO']['id']            
            vals['date_invoice'] = xml_dicts[2]['FchEmis']
            vals['date_due'] = xml_dicts[2]['FchVenc']
            vals['currency_id'] = divisa[0]
            vals['account_id'] = account_id
            vals['supplier_invoice_number'] = xml_dicts[2]['Folio']
            inv_id = invoice_dte.create(cr,uid,vals,context)            
        except:
            print "fallo al crear factura_dte"    

#Crear lineas de Factura A Partir del archivo XML        
        for line in xml_dicts[7]:
            try:                                     
                if xml_dicts[6]['TasaIVA'] and xml_dicts[1]['TpoDTE'] != 34:
                    iva = 1.19
                else: iva = 1
                vals_line['name'] = line['NmbItem']
                vals_line['account_id'] = default_account
                vals_line['price_unit'] = line['PrcItem'] if  line['PrcItem'] else float(line['MontoItem']) / iva 
                vals_line['quantity'] = line['QtyItem'] if line['QtyItem'] else 1.0             
                vals_line['invoice_id'] = inv_id 
                vals_line = invoice_dte_line.create(cr,uid,vals_line)
                if iva > 1 :
                    cr.execute("""INSERT INTO account_invoice_line_dte_tax(
                                invoice_line_id, tax_id)
                                VALUES (%d, %d);
                                """% (vals_line,default_iva))

                vals_line = {'name' : False,'account_id' : False , 'quantity' : 1.0, 'price_unit': False ,'invoice_line_tax_id' : [] }            
            except:                            
                print "fallo al crear factura_dte"
                continue
        invoice_dte.button_reset_taxes(cr,uid,[inv_id],context)    
    
    def buscar_cuentas_defecto_factDte(self, cr, type, res_partner):
        if type == 'compra':
            account_id = res_partner.property_account_payable.id
            cr.execute("SELECT account_proveedor_default FROM config_dte_invoice WHERE state = True ")
            default_account = cr.fetchone()
        else:
            account_id = res_partner.property_account_receivable.id
            cr.execute("SELECT account_client_default FROM config_dte_invoice WHERE state = True ")
            default_account = cr.fetchone()
        return account_id,default_account

    def buscar_iva_defecto_factDte(self, cr, type, res_partner):
        if type == 'compra':
            cr.execute("SELECT iva_credito FROM config_dte_invoice WHERE state = True ")
            default_account = cr.fetchone()[0]
        else:
            cr.execute("SELECT iva_debito FROM config_dte_invoice WHERE state = True ")
            default_account = cr.fetchone()[0]
        return default_account

   

    def buscar_divisa(self,cr):
        cr.execute("SELECT id FROM res_currency WHERE name like 'CLP'")
        return cr.fetchone()


    def buscar_proveedor_cliente(self,cr,uid,rut,context=None):           
        rut_vat_mod = "%"+ str(rut)
        cr.execute("SELECT id FROM res_partner where vat like \'%s\'" % rut_vat_mod)
        return cr.fetchone()
    
    #si partner de xml sii no se encuentra en el sistema se crea

    
    def crear_partner(self, cr, uid, data,customer,supplier):
        values = {'name': data['RznSoc'], 'vat':'cl%s'% self.validar_rut(data['RUTEmisor']),
                  'is_company':True,'giro':data['GiroEmis'],
                  'street':data['DirOrigen'],'active':True,'customer':customer,'supplier':supplier}
        partner = self.pool.get('res.partner').create(cr,uid, values) 
        return partner
        
    
    #Esta funcion recive el rut y lo transforma para que solo queden numeros
    # y el dijito verificador        

    
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
        return vat


    def buscar_partner_usuario_correo_sii(self, cr, uid ,context = None):
        cr.execute("""select partner_id from res_users where user_sii_mail = true limit 1""")
        partner_id = cr.fetchone()
        return partner_id 
    
    
    def buscar_notificaciones(self, cr,  user_id_correo):
        cr.execute('SELECT message_id FROM mail_notification where partner_id = %d and read is not True' % user_id_correo)
        notification_ids=cr.fetchall()
        if not notification_ids: return []
        message_id = []
        if notification_ids[0]:
            for record in notification_ids:                 
                message_id.append(record[0])
        return message_id
                
mail_message()    
