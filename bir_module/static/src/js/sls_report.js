/** @odoo-module **/

import { Component, onWillStart, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { construct_sls, get_current } from "./bir_utils";

// SLS Report Component
export class SLSReport extends Component {
  static template = "bir_module.sls_report";

  setup() {
    this.orm = useService("orm");
    this.notification = useService("notification");
    this.rootRef = useRef("root");

    this.state = useState({
      currentMonth: get_current(),
    });

    onWillStart(async () => {
      await this.loadReport();
    });
  }

  async loadReport() {
    const monthInput = this.rootRef.el?.querySelector("#sls_param");
    const current = monthInput ? monthInput.value : this.state.currentMonth;

    const data = await this.orm.call("account.move", "SLS_SLP_report", [
      "",
      current,
      "out_invoice",
    ]);

    const slsTable = this.rootRef.el?.querySelector("#sls_table");
    if (slsTable) {
      slsTable.innerHTML = construct_sls(data);
      if (window.jQuery) {
        window.jQuery("#sls_datatable").DataTable();
        window.jQuery(".dataTables_length").addClass("bs-select");
      }
    }
  }

  async onSlsParamKeypress(ev) {
    if (ev.which === 13) {
      await this.loadReport();
    }
  }

  async onExportSls() {
    const monthInput = this.rootRef.el.querySelector("#sls_param");
    const current = monthInput ? monthInput.value : this.state.currentMonth;

    // Uncomment and implement when backend method is ready
    // const data = await this.orm.call('account.move', 'export_sls',
    //     ['', current]
    // );
    // this.notification.add(data, {
    //     type: 'info',
    // });

    this.notification.add("Export functionality not yet implemented", {
      type: "warning",
    });
  }
}

registry.category("actions").add("sls_report_page", SLSReport);
