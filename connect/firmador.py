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
from OpenSSL import crypto
from OpenSSL.crypto import load_pkcs12, FILETYPE_PEM, FILETYPE_ASN1
from signxml import xmldsig
import signxml
import xml.etree.ElementTree as ET
from lxml import etree
#apt-get install xmlsec1
#pip install signxml
#apt-get install python-dev libxml2-dev libxslt1-dev libssl-dev python-cffi
#pip install enum34
#pip install eight
#pip install defusedxml
#pip install cryptography
#pip install certifi
#pip install --upgrade pyopenssl
import os


def _entregaFirma (self,xml_factura):
    path = os.getcwd() + '/openerp/v7/addons_econube/account_invoice_cl/connect/firma/%s'
    p12 = path % 'contact people.pfx' #'cert_econube_2016.p12'
    p12 = crypto.load_pkcs12(file(p12, 'rb').read(), 'chiledar')
    certificate = p12.get_certificate()
    private_key = p12.get_privatekey()
    type_ = FILETYPE_PEM
    signature = certificate.get_signature_algorithm()
    type_pk = private_key.type()
    str_private_key=crypto.dump_privatekey(type_, private_key)
    str_certificate_key=crypto.dump_certificate(type_, certificate)
    fields = certificate.get_subject().get_components()
    root = etree.fromstring(xml_factura.strip())
    xmldsig(root).sign(algorithm='rsa-sha1',key=str_private_key, cert=str_certificate_key,c14n_algorithm='REC-xml-c14n-20010315')
    xml_firmado =  etree.tostring(root,encoding="ISO-8859-1", method="xml")
    verified_data = xmldsig(xml_firmado).verify(x509_cert=str_certificate_key)
    xml_verificado =  etree.tostring(verified_data,encoding="ISO-8859-1", method="xml")
#    client = _connect_GetTokenFromSeed()                 
#    res = client.service.getToken(xml_verificado)
#    xml_verificado =  etree.tostring(verified_data, pretty_print = True, method="xml")
#    res = etree.tostring(res, pretty_print = True, method="xml")
    return xml_verificado


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:#
