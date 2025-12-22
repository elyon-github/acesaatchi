/** @odoo-module */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

export class AccruedRevenue_Lines_ListController extends ListController {
  setup() {
    super.setup();
    this.actionService = useService("action");
  }

  /**
   * Open the Accrued Revenue Report wizard
   */
  async onPrintAccruedRevenue() {
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
  }

  /**
   * Open the Sales Order Revenue Report wizard
   */
  async onPrintSalesOrderRevenue() {
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