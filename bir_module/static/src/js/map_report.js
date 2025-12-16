/** @odoo-module **/

import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { construct_sawt, get_current } from "./bir_utils";

// MAP Report Component
export class MAPReport extends Component {
  static template = "bir_module.map_report";

  setup() {
    this.orm = useService("orm");
    this.notification = useService("notification");
    this.rootRef = useRef("root");

    this.state = useState({
      currentMonth: get_current(),
    });

    onMounted(async () => {
      await this.loadReport();
    });
  }

  async loadReport() {
    const monthInput = this.rootRef.el.querySelector("#map_param");
    const current = monthInput ? monthInput.value : this.state.currentMonth;

    const data = await this.orm.call("account.move", "MAP_report", [
      "",
      current,
    ]);

    const mapTable = this.rootRef.el.querySelector("#map_table");
    if (mapTable) {
      mapTable.innerHTML = construct_sawt(data);
      if (window.jQuery) {
        window.jQuery("#sawt_datatable").DataTable();
        window.jQuery(".dataTables_length").addClass("bs-select");
      }
    }
  }

  async onMapParamKeypress(ev) {
    if (ev.which === 13) {
      await this.loadReport();
    }
  }

  async onExportMap() {
    const monthInput = this.rootRef.el.querySelector("#map_param");
    const current = monthInput ? monthInput.value : this.state.currentMonth;

    const data = await this.orm.call("account.move", "export_sawt_map", [
      "",
      current,
      "map",
    ]);

    this.notification.add(data, {
      type: "info",
    });
  }

  async onExportMapCsv() {
    const monthInput = this.rootRef.el.querySelector("#map_param");
    const current = monthInput ? monthInput.value : this.state.currentMonth;

    const data = await this.orm.call("account.move", "export_sawt_map_csv", [
      "",
      current,
      "map",
    ]);

    this.notification.add(data, {
      type: "info",
    });
  }
}

registry.category("actions").add("map_report_page", MAPReport);
