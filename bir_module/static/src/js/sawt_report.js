/** @odoo-module **/

import { Component, onWillStart, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { construct_sawt, get_current } from "./bir_utils";

// SAWT Report Component
export class SAWTReport extends Component {
  static template = "bir_module.sawt_report";

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
    const monthInput = this.rootRef.el?.querySelector("#sawt_param");
    const current = monthInput ? monthInput.value : this.state.currentMonth;

    const data = await this.orm.call("account.move", "SAWT_report", [
      "",
      current,
    ]);

    const sawtTable = this.rootRef.el?.querySelector("#sawt_table");
    if (sawtTable) {
      sawtTable.innerHTML = construct_sawt(data);
      if (window.jQuery) {
        window.jQuery("#sawt_datatable").DataTable();
        window.jQuery(".dataTables_length").addClass("bs-select");
      }
    }
  }

  async onSawtParamKeypress(ev) {
    if (ev.which === 13) {
      await this.loadReport();
    }
  }

  async onExportSawt() {
    const monthInput = this.rootRef.el.querySelector("#sawt_param");
    const current = monthInput ? monthInput.value : this.state.currentMonth;

    const data = await this.orm.call("account.move", "export_sawt_map", [
      "",
      current,
      "sawt",
    ]);

    this.notification.add(data, {
      type: "info",
    });
  }

  async onExportSawtCsv() {
    const monthInput = this.rootRef.el.querySelector("#sawt_param");
    const current = monthInput ? monthInput.value : this.state.currentMonth;

    const data = await this.orm.call("account.move", "export_sawt_map_csv", [
      "",
      current,
      "sawt",
    ]);

    this.notification.add(data, {
      type: "info",
    });
  }
}

registry.category("actions").add("sawt_report_page", SAWTReport);
