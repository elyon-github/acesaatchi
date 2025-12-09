/** @odoo-module **/

import { Component, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
  construct_print_details,
  construct_print_history,
  construct_print_types,
} from "./bir_utils";

// Print History Component
export class PrintHistory extends Component {
  static template = "bir_module.print_history";

  setup() {
    this.orm = useService("orm");
    this.rootRef = useRef("root");

    onMounted(async () => {
      await this.loadInitialData();
    });
  }

  async loadInitialData() {
    const typesData = await this.orm.call("account.move", "fetch_print_types", [
      "",
    ]);
    const printTypeSelect = this.rootRef.el.querySelector("#print_type");
    if (printTypeSelect) {
      printTypeSelect.innerHTML = construct_print_types(typesData);
    }

    const historyData = await this.orm.call(
      "account.move",
      "fetch_print_history",
      ["", "all"]
    );
    const printHistoryDiv = this.rootRef.el.querySelector("#print_history");
    if (printHistoryDiv) {
      printHistoryDiv.innerHTML = construct_print_history(historyData, this);
      if (window.jQuery) {
        window.jQuery("#print_history_datatable").DataTable();
        window.jQuery(".dataTables_length").addClass("bs-select");
      }
    }
  }

  async onPrintTypeChange() {
    const printTypeSelect = this.rootRef.el.querySelector("#print_type");
    const type = printTypeSelect ? printTypeSelect.value : "all";

    const historyData = await this.orm.call(
      "account.move",
      "fetch_print_history",
      ["", type]
    );
    const printHistoryDiv = this.rootRef.el.querySelector("#print_history");
    if (printHistoryDiv) {
      printHistoryDiv.innerHTML = construct_print_history(historyData, this);
      if (window.jQuery) {
        window.jQuery("#print_history_datatable").DataTable();
        window.jQuery(".dataTables_length").addClass("bs-select");
      }
    }
  }

  async onPrintDetailsClick(ev) {
    const button = ev.target.closest("button");
    const cellVal = button ? button.value : null;

    if (cellVal) {
      const detailsData = await this.orm.call(
        "account.move",
        "fetch_print_history_details",
        ["", cellVal]
      );
      const printDetailsDiv = this.rootRef.el.querySelector("#print_details");
      if (printDetailsDiv) {
        printDetailsDiv.innerHTML = construct_print_details(detailsData);
        if (window.jQuery) {
          window.jQuery("#print_history_line_datatable").DataTable();
          window.jQuery(".dataTables_length").addClass("bs-select");
        }
      }
    }
  }

  async onPreviewDetailsClick(ev) {
    const button = ev.target.closest("button");
    const cellVal = button ? button.value : null;

    if (cellVal) {
      const data = await this.orm.call("account.move", "get_reprint_trans", [
        "",
        cellVal,
      ]);
      let url = "";

      if (data[0] === "2550M") {
        url =
          "/report/pdf/bir_module.form_2550M?month=" +
          data[1] +
          "&trans=2550M&trigger=reprint&tranid=" +
          cellVal;
      } else if (data[0] === "2550Q") {
        url =
          "/report/pdf/bir_module.form_2550Q?month=" +
          data[1] +
          "&trans=2550Q&trigger=reprint&tranid=" +
          cellVal;
      } else if (data[0] === "2307-Transactional") {
        url =
          "/report/pdf/bir_module.form_2307_preview/?id=none&month=" +
          data[1] +
          "&type=" +
          data[0] +
          "&tranid=" +
          cellVal;
      } else if (data[0] === "2307-Quarterly") {
        url =
          "/report/pdf/bir_module.form_2307_preview/?id=none&month=" +
          data[1] +
          "&type=" +
          data[0] +
          "&tranid=" +
          cellVal;
      }

      const previewFrame = this.rootRef.el.querySelector(
        "#print_preview_frame"
      );
      if (previewFrame) {
        previewFrame.src = url;
      }
    }
  }
}

registry.category("actions").add("print_history_page", PrintHistory);
