/** @odoo-module **/

import { Component, onWillStart, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { construct_slp, get_current } from "./bir_utils";

// SLP Report Component
export class SLPReport extends Component {
  static template = "bir_module.slp_report";

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
    const monthInput = this.rootRef.el?.querySelector("#slp_param");
    const current = monthInput ? monthInput.value : this.state.currentMonth;

    const data = await this.orm.call("account.move", "SLS_SLP_report", [
      "",
      current,
      "in_invoice",
    ]);

    const slpTable = this.rootRef.el?.querySelector("#slp_table");
    if (slpTable) {
      slpTable.innerHTML = construct_slp(data);
      if (window.jQuery) {
        window.jQuery("#slp_datatable").DataTable();
        window.jQuery(".dataTables_length").addClass("bs-select");
      }
    }
  }

  async onSlpParamKeypress(ev) {
    if (ev.which === 13) {
      await this.loadReport();
    }
  }

  async onExportSlp() {
    const monthInput = this.rootRef.el.querySelector("#slp_param");
    const current = monthInput ? monthInput.value : this.state.currentMonth;

    // Uncomment and implement when backend method is ready
    // const data = await this.orm.call('account.move', 'export_slp',
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

registry.category("actions").add("slp_report_page", SLPReport);
