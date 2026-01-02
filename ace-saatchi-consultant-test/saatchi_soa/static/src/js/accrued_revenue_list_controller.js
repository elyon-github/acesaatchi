/** @odoo-module */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { user } from "@web/core/user";
import { useState } from "@odoo/owl";

export class AccruedRevenue_Lines_ListController extends ListController {
  setup() {
    super.setup();
    this.actionService = useService("action");
    this.state = useState({
      hasAccruedRevenueAccess: false
    });
    
    // Check permission asynchronously
    this.checkAccess();
  }
  
  async checkAccess() {
    this.state.hasAccruedRevenueAccess = await user.hasGroup('account.group_account_manager');
  }
  
  get hasAccruedRevenueAccess() {
    return this.state.hasAccruedRevenueAccess;
  }
  
  /**
   * Open the Accrued Revenue Report wizard
   */
  async onPrintAccruedRevenue() {
    // Double-check permission
    const hasAccess = await user.hasGroup('account.group_account_manager');
    if (!hasAccess) {
      return;
    }
    
    // Open the wizard
    await this.actionService.doAction({
      type: "ir.actions.act_window",
      res_model: "accrued.revenue_report.wizard",
      view_mode: "form",
      views: [[false, "form"]],
      target: "new",
      name: "Generate Accrued Revenue Report",
    });
  }
}

// Link controller to the template with buttons - FIXED NAME
AccruedRevenue_Lines_ListController.template =
  "saatchi_soa.AccruedRevenueLinesListView.Buttons";

export const accruedRevenueListView = {
  ...listView,
  Controller: AccruedRevenue_Lines_ListController,
};

// Register the custom list view
registry
  .category("views")
  .add("accrued_revenue_list_view", accruedRevenueListView);

export class SalesOrderRevenueListController extends ListController {
  setup() {
    super.setup();
    this.actionService = useService("action");
    this.state = useState({
      hasSalesOrderRevenueAccess: false
    });
    
    // Check permission asynchronously
    this.checkAccess();
  }
  
  async checkAccess() {
    this.state.hasSalesOrderRevenueAccess = await user.hasGroup('account.group_account_manager');
  }
  
  get hasSalesOrderRevenueAccess() {
    return this.state.hasSalesOrderRevenueAccess;
  }
  
  /**
   * Open the Sales Order Revenue Report wizard
   */
  async onPrintSalesOrderRevenue() {
    // Double-check permission
    const hasAccess = await user.hasGroup('account.group_account_manager');
    if (!hasAccess) {
      return;
    }
    
    // Open the wizard
    await this.actionService.doAction({
      type: "ir.actions.act_window",
      res_model: "sales.order.revenue_report.wizard",
      view_mode: "form",
      views: [[false, "form"]],
      target: "new",
      name: "Generate Sales Order Revenue Report",
    });
  }
}

// Link controller to the template with buttons
SalesOrderRevenueListController.template =
  "saatchi_soa.SalesOrderRevenueListView.Buttons";

export const salesOrderRevenueListView = {
  ...listView,
  Controller: SalesOrderRevenueListController,
};

// Register the custom list view
registry
  .category("views")
  .add("sales_order_revenue_list_view", salesOrderRevenueListView);