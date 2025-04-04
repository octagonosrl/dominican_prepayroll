# -*- coding: utf-8 -*-

from odoo import api, fields, models
from datetime import datetime
import base64
import xlsxwriter

INCOME_TYPE = {
    '1': 'Normal',
    '2': 'Trabajador ocasional (no fijo)',
    '3': 'Asalariado por hora o labora tiempo parcial',
    '4': 'No laboró mes completo por razones varias',
    '5': 'Salario prorrateado semanal/bisemanal',
    '6': 'Pensionado antes de la Ley 87-01',
    '7': 'Exento por Ley de pago al SDSS',
}

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    is_prepayroll = fields.Boolean(string='Es Prenómina')

    @api.model
    def create(self, values):
        to_unlink = self.sudo().env['hr.payslip'].search([('is_prepayroll', '=', True)])
        if 'is_prepayroll' in values and not values.get('is_prepayroll') and to_unlink:
            to_unlink.sudo().unlink()

        return super(HrPayslip, self).create(values)


class PrePayrollUWizard(models.TransientModel):
    _name = 'pre.payroll.user.wizard'
    _description = 'Wizards de Pre Nómina'

    employee_vat = fields.Char(string='Cédula')
    contract_id = fields.Many2one('hr.contract', string='Contrato del empleado')
    struct_id = fields.Many2one('hr.payroll.structure', string='Estructura Salarial')
    report_type = fields.Selection([('pdf', 'PDF'), ('xlsx', 'Excel')], string='Tipo de reporte', required=True, default='pdf')

    payslip_report_xlsx_file_name = fields.Char()
    payslip_report_xlsx_binary = fields.Binary(string="Reporte de nómina XLS")

    def create_report(self):
        to_unlink = self.env['hr.payslip'].sudo().search([('is_prepayroll', '=', True)])
        if to_unlink:
            to_unlink.sudo().unlink()

        if datetime.today().day >= 15:
            date_from = datetime.today().date().replace(day=15)
        else:
            date_from = datetime.today().date().replace(day=1)

        date_to = datetime.today().date()

        employee_ids = self.env['hr.employee'].sudo().search([('identification_id', '=', self.employee_vat)], limit=1)

        hr_payslip = self.env['hr.payslip'].sudo()

        for employee_id in employee_ids:
            self.sudo().contract_id = employee_id.sudo().contract_id
            self.sudo().struct_id = employee_id.sudo().contract_id.struct_id

            hr_payslip += hr_payslip.sudo().create({
                'employee_id': employee_id.id,
                'date_from': date_from,
                'date_to': date_to,
                'contract_id': self.contract_id.id,
                'struct_id': self.struct_id.id,
                'is_prepayroll': True,
            })

        for rec in hr_payslip:
            rec.sudo().onchange_employee()
            rec.sudo().compute_sheet()

        if self.sudo().report_type == 'pdf':
            report_pdf = self.env.ref('hr_payroll.action_report_payslip').sudo().report_action(hr_payslip.ids, config=False)
            return report_pdf

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'pre.payroll.wizard',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': this.id,
                'views': [(False, 'form')],
                'target': 'new',
            }


class PrePayrollMWizard(models.TransientModel):
    _name = 'pre.payroll.manager.wizard'
    _description = 'Wizards de Pre Nómina'

    contract_id = fields.Many2one('hr.contract', string='Contrato del empleado')
    employee_ids = fields.Many2many('hr.employee', string='Empleados')
    struct_id = fields.Many2one('hr.payroll.structure', string='Estructura Salarial')
    department_id = fields.Many2many(comodel_name='hr.department', string='Departamento')
    all_departments = fields.Boolean(string='Todos los Departamentos')
    report_type = fields.Selection([('pdf', 'PDF'), ('xlsx', 'Excel')], string='Tipo de reporte', required=True, default='pdf')

    payslip_report_xlsx_file_name = fields.Char()
    payslip_report_xlsx_binary = fields.Binary(string="Reporte de nómina XLS")

    def create_report(self):
        to_unlink = self.env['hr.payslip'].sudo().search([('is_prepayroll', '=', True)])
        if to_unlink:
            to_unlink.sudo().unlink()

        if datetime.today().day >= 15:
            date_from = datetime.today().date().replace(day=15)
        else:
            date_from = datetime.today().date().replace(day=1)

        date_to = datetime.today().date()

        employee_ids = self.employee_ids

        if self.all_departments:
            employee_ids = self.env['hr.employee'].sudo().search([
                ('department_id', 'in', self.env['hr.department'].sudo().search([
                    ('active', '=', True)]).ids)
            ])

        elif self.department_id:
            employee_ids = self.env['hr.employee'].sudo().search([('department_id', 'in', self.department_id.ids)])

        hr_payslip = self.env['hr.payslip'].sudo()

        for employee_id in employee_ids:
            self.sudo().contract_id = employee_id.sudo().contract_id
            self.sudo().struct_id = employee_id.sudo().contract_id.struct_id

            hr_payslip += hr_payslip.sudo().create({
                'employee_id': employee_id.id,
                'date_from': date_from,
                'date_to': date_to,
                'contract_id': self.contract_id.id,
                'struct_id': self.struct_id.id,
                'is_prepayroll': True,
            })

        for rec in hr_payslip:
            rec.sudo().onchange_employee()
            rec.sudo().compute_sheet()

        if self.sudo().report_type == 'pdf':
            report_pdf = self.env.ref('hr_payroll.action_report_payslip').sudo().report_action(hr_payslip.ids, config=False)
            return report_pdf

        elif self.report_type == 'xlsx':
            this = self[0]

            employee_list = []
            for rec in hr_payslip:
                if rec.employee_id.id not in employee_list:
                    employee_list.append(rec.employee_id.id)

            file_header = ['Fecha',
                           u'Cédula',
                           'Empleado',
                           'Tipo de ingreso',
                           'Cuenta Analitica',
                           'Salario Mensual',
                           'Salario Quincenal',
                           'Horas Extras',
                           'Incentivos',
                           'Vacaciones',
                           'Comisiones',
                           'Financiera',
                           'Otros descuentos',
                           'Avances',
                           u'Seguro Complementario',
                           u'Retención AFP',
                           u'Retención SFS',
                           u'Retención ISR',
                           'Saldo a Favor ISR',
                           'Salario Cotizable ISR',
                           'Salario Cotizable TSS/INFOTEP',
                           u'Contribución AFP',
                           u'Contribución SFS',
                           u'Contribución SRL',
                           u'Contribución INFOTEP',
                           u'Cafetería',
                           u'Farmacia',
                           u'Ahorro',
                           u'Restaurante',
                           'Salario a pagar']

            records = []
            for i in employee_list:
                for rec in hr_payslip.filtered(lambda payslip: payslip.employee_id.id == i):
                    records.append([rec.date_to,
                                    rec.employee_id.identification_id or '',
                                    rec.employee_id.name,
                                    INCOME_TYPE.get(rec.employee_id.income_type),
                                    rec.contract_id.analytic_account_id.name or '',
                                    rec.line_ids.filtered(
                                        lambda line_ids: line_ids.code in ['BASIC', 'BAEX']).total * 2 or 0.0,
                                    rec.line_ids.filtered(
                                        lambda line_ids: line_ids.code in ['BASIC', 'BAEX']).total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'HOREX').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'INCENT').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'VACA').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'COMM').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'FINAN').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'OTDESC').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'AVAN').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'SEGMED').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'SVDS').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'SFST').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'ISR').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'SFISR').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'SCISR').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'GROSS').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'SVDS E').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'SFS E').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'SRL E').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'CINF').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'CAFE').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'FARMA').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'AHORRO').total or 0.0,
                                    rec.line_ids.filtered(lambda line_ids: line_ids.code == 'REST').total or 0.0,
                                    rec.line_ids.filtered(
                                        lambda line_ids: line_ids.code in ['NET', 'NETEX']).total or 0.0])

            file_path = '/tmp/REPORTE PRE NOMINA desde {} a {}.xlsx'.format(date_to, date_from)
            workbook = xlsxwriter.Workbook(file_path, {'strings_to_numbers': True})
            worksheet = workbook.add_worksheet()
            # Add a bold format to use to highlight cells.
            bold = workbook.add_format({'bold': 1})

            for col_num, data in enumerate(file_header):
                worksheet.write(0, col_num, data)

            row = 1
            for rec in records:
                for col, detail in enumerate(rec):
                    worksheet.write(row, col, detail)
                row += 1

            workbook.close()

            this.write({
                'payslip_report_xlsx_file_name': file_path.replace('/tmp/', ''),
                'payslip_report_xlsx_binary': base64.b64encode(open(file_path, 'rb').read())
            })

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'pre.payroll.manager.wizard',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': this.id,
                'views': [(False, 'form')],
                'target': 'new',
            }


class PrePayRoll(models.Model):
    _name = 'pre.payroll'
    _description = 'Pre Nomina'

    employee_id = fields.Char(string='Empleado')
