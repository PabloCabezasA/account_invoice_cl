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

from suds.client import Client

def _connect_soap (self, cr, uid, ids):
    config_ids = self.pool.get("account.config.firma").search(cr,uid,[("id","!=","0")])
    config = self.pool.get("account.config.firma").read(cr, uid, config_ids,['connect'])[0]
    client = Client(config['connect'])
    client.set_options(location=config['connect'])
    return (client)

#web service CrSeed permite obtener semilla
def _connect_CrSeed (self):
#    url ="https://palena.sii.cl/DTEWS/CrSeed.jws?wsdl"
    url= "https://maullin.sii.cl/DTEWS/CrSeed.jws?WSDL"
    client = Client(url) 
    client.set_options(location=url)
    return (client)

#web service CrSeed permite obtener token
def _connect_GetTokenFromSeed (self):
#    url ="https://palena.sii.cl/DTEWS/GetTokenFromSeed.jws?WSDL"
    url ="https://maullin.sii.cl/DTEWS/GetTokenFromSeed.jws?WSDL"
    client = Client(url) 
    client.set_options(location=url)
    return (client)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:#