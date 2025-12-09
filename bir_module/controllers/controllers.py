# -*- coding: utf-8 -*-
from odoo import http


class BirModule(http.Controller):
    @http.route('/bir_module/bir_module/', auth='public')
    def index(self, **kw):
        return "Hello, world"

    @http.route('/bir_module/bir_module/objects/', auth='public')
    def list(self, **kw):
        return http.request.render('bir_module.listing', {
            'root': '/bir_module/bir_module',
            'objects': http.request.env['bir_module.bir_module'].search([]),
        })

    @http.route('/bir_module/bir_module/objects/<model("bir_module.bir_module"):obj>/', auth='public')
    def object(self, obj, **kw):
        return http.request.render('bir_module.object', {
            'object': obj
        })
