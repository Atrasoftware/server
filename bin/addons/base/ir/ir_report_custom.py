##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import fields,osv
from osv.orm import browse_null
import ir
import report.custom
from tools.translate import _

class report_custom(osv.osv):
	_name = 'ir.report.custom'
	_columns = {
		'name': fields.char('Report Name', size=64, required=True, translate=True),
		'model_id': fields.many2one('ir.model','Model', required=True, change_default=True),
		'type': fields.selection([('table','Tabular'),('pie','Pie Chart'),('bar','Bar Chart'),('line','Line Plot')], "Report Type", size=64, required='True'),
		'title': fields.char("Report title", size=64, required='True', translate=True),
		'print_format': fields.selection((('A4','a4'),('A5','a5')), 'Print format', required=True),
		'print_orientation': fields.selection((('landscape','Landscape'),('portrait','Portrait')), 'Print orientation', required=True, size=16),
		'repeat_header': fields.boolean('Repeat Header'),
		'footer': fields.char('Report Footer', size=64, required=True),
		'sortby': fields.char('Sorted By', size=64),
		'fields_child0': fields.one2many('ir.report.custom.fields', 'report_id','Fields', required=True),
		'field_parent': fields.many2one('ir.model.fields','Child Field'),
		'state': fields.selection([('unsubscribed','Unsubscribed'),('subscribed','Subscribed')], 'State', size=64),
		'frequency': fields.selection([('Y','Yearly'),('M','Monthly'),('D','Daily')], 'Frequency', size=64),
		'limitt': fields.char('Limit', size=9),
		'menu_id': fields.many2one('ir.ui.menu', 'Menu')
	}
	_defaults = {
		'print_format': lambda *a: 'A4',
		'print_orientation': lambda *a: 'portrait',
		'state': lambda *a: 'unsubscribed',
		'type': lambda *a: 'table',
		'footer': lambda *a: 'Generated by Tiny ERP'
	}
	
	def onchange_model_id(self, cr, uid, ids, model_id):
		if not(model_id):
			return {}
		return {'domain': {'field_parent': [('model_id','=',model_id)]}}

	def unsubscribe(self, cr, uid, ids, context={}):
#TODO: should delete the ir.actions.report.custom for these reports and do an ir_del
		self.write(cr, uid, ids, {'state':'unsubscribed'})
		return True

	def subscribe(self, cr, uid, ids, context={}):
		for report in self.browse(cr, uid, ids):
			report.fields_child0.sort(lambda x,y : x.sequence - y.sequence)
		
			# required on field0 does not seem to work( cause we use o2m_l ?)
			if not report.fields_child0:
				raise osv.except_osv(_('Invalid operation'), _('Enter at least one field !'))
			
			if report.type in ['pie', 'bar', 'line'] and report.field_parent:
				raise osv.except_osv(_('Invalid operation'), _('Tree can only be used in tabular reports'))
			
			# Otherwise it won't build a good tree. See level.pop in custom.py.
			if report.type == 'table' and report.field_parent and report.fields_child0 and not report.fields_child0[0].groupby:
				raise osv.except_osv('Invalid operation :', 'When creating tree (field child) report, data must be group by the first field')

			if report.type == 'pie':
				if len(report.fields_child0) != 2:
					raise osv.except_osv(_('Invalid operation'), _('Pie charts need exactly two fields'))
				else:
					c_f = {}
					for i in range(2):
						c_f[i] = []
						tmp = report.fields_child0[i]
						for j in range(3):
							c_f[i].append((not isinstance(eval('tmp.field_child'+str(j)), browse_null) and eval('tmp.field_child'+str(j)+'.ttype')) or None)
					if not reduce(lambda x,y : x or y, map(lambda x: x in ['integer', 'float'], c_f[1])):
						raise osv.except_osv(_('Invalid operation'), _('Second field should be figures'))
					
			if report.type == 'bar':
				if len(report.fields_child0) < 2:
					raise osv.except_osv(_('Invalid operation'), _('Bar charts need at least two fields'))
				else:
					c_f = {}
					for i in range(len(report.fields_child0)):
						c_f[i] = []
						tmp = report.fields_child0[i]
						for j in range(3):
							c_f[i].append((not isinstance(eval('tmp.field_child'+str(j)), browse_null) and eval('tmp.field_child'+str(j)+'.ttype')) or None)

						if i == 0:
							pass
						else:
							if not reduce(lambda x,y : x or y, map(lambda x: x in ['integer', 'float'], c_f[i])):
								raise osv.except_osv(_('Invalid operation'), _('Field %d should be a figure') %(i,))

			if report.state=='subscribed':
				continue

			name = report.name
			model = report.model_id.model

			action_def = {'report_id':report.id, 'type':'ir.actions.report.custom', 'model':model, 'name':name}
			id = self.pool.get('ir.actions.report.custom').create(cr, uid, action_def)
			m_id = report.menu_id.id
			action = "ir.actions.report.custom,%d" % (id,)
			if not report.menu_id:
				ir.ir_set(cr, uid, 'action', 'client_print_multi', name, [(model, False)], action, False, True)
			else:
				ir.ir_set(cr, uid, 'action', 'tree_but_open', 'Menuitem', [('ir.ui.menu', int(m_id))], action, False, True)

			self.write(cr, uid, [report.id], {'state':'subscribed'}, context)
		return True
report_custom()


class report_custom_fields(osv.osv):
	_name = 'ir.report.custom.fields'
	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'report_id': fields.many2one('ir.report.custom', 'Report Ref', select=True),
		'field_child0': fields.many2one('ir.model.fields', 'field child0', required=True),
		'fc0_operande': fields.many2one('ir.model.fields', 'Constraint'), 
		'fc0_condition': fields.char('Condition', size=64),
		'fc0_op': fields.selection((('>','>'),('<','<'),('==','='),('in','in'),('gety,==','(year)=')), 'Relation'),
		'field_child1': fields.many2one('ir.model.fields', 'field child1'),
		'fc1_operande': fields.many2one('ir.model.fields', 'Constraint'), 
		'fc1_condition': fields.char('condition', size=64),
		'fc1_op': fields.selection((('>','>'),('<','<'),('==','='),('in','in'),('gety,==','(year)=')), 'Relation'),
		'field_child2': fields.many2one('ir.model.fields', 'field child2'),
		'fc2_operande': fields.many2one('ir.model.fields', 'Constraint'), 
		'fc2_condition': fields.char('condition', size=64),
		'fc2_op': fields.selection((('>','>'),('<','<'),('==','='),('in','in'),('gety,==','(year)=')), 'Relation'),
		'field_child3': fields.many2one('ir.model.fields', 'field child3'),
		'fc3_operande': fields.many2one('ir.model.fields', 'Constraint'), 
		'fc3_condition': fields.char('condition', size=64),
		'fc3_op': fields.selection((('>','>'),('<','<'),('==','='),('in','in'),('gety,==','(year)=')), 'Relation'),
		'alignment':  fields.selection((('left','left'),('right','right'),('center','center')), 'Alignment', required=True),
		'sequence': fields.integer('Sequence', required=True),
		'width': fields.integer('Fixed Width'),
		'operation': fields.selection((('none', 'None'),('calc_sum','Calculate Sum'),('calc_avg','Calculate Average'),('calc_count','Calculate Count'),('calc_max', 'Get Max'))),
		'groupby' : fields.boolean('Group by'),
		'bgcolor': fields.char('Background Color', size=64),
		'fontcolor': fields.char('Font color', size=64),
		'cumulate': fields.boolean('Cumulate')
	}
	_defaults = {
		'alignment': lambda *a: 'left',
		'bgcolor': lambda *a: 'white',
		'fontcolor': lambda *a: 'black',
		'operation': lambda *a: 'none',
	}
	_order = "sequence"

	def onchange_any_field_child(self, cr, uid, ids, field_id, level):
		if not(field_id):
			return {}
		next_level_field_name = 'field_child%d' % (level+1)
		next_level_operande = 'fc%d_operande' % (level+1)
		field = self.pool.get('ir.model.fields').browse(cr, uid, [field_id])[0]
		res = self.pool.get(field.model).fields_get(cr, uid, field.name)
		if res[field.name].has_key('relation'):
			cr.execute('select id from ir_model where model=%s', (res[field.name]['relation'],))
			(id,) = cr.fetchone() or (False,)
			if id:
				return {
					'domain': {
						next_level_field_name: [('model_id', '=', id)], 
						next_level_operande: [('model_id', '=', id)]
					}, 
					'required': {
						next_level_field_name: True
					}
				}
			else:
				print _("Warning: using a relation field which uses an unknown object")	#TODO use the logger
				return {'required': {next_level_field_name: True}}
		else:
			return {'domain': {next_level_field_name: []}}
			
	def get_field_child_onchange_method(level):
		return lambda self, cr, uid, ids, field_id: self.onchange_any_field_child(cr, uid, ids, field_id, level)

	onchange_field_child0 = get_field_child_onchange_method(0)	
	onchange_field_child1 = get_field_child_onchange_method(1)	
	onchange_field_child2 = get_field_child_onchange_method(2)	
report_custom_fields()

