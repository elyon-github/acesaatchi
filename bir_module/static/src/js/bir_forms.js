/** @odoo-module **/

import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
  construct_ammendment,
  construct_ammendment_no_action,
  construct_partners,
  get_current,
} from "./bir_utils";

// Form 2307 Component
export class Form2307 extends Component {
  static template = "bir_module.form_2307_page";

  setup() {
    this.orm = useService("orm");
    this.action = useService("action");
    this.rootRef = useRef("root");

    this.state = useState({
      currentMonth: get_current(),
      selectedPartner: 0,
    });

    onMounted(async () => {
      await this.loadInitialData();
    });
  }

  async loadInitialData() {
    const data = await this.orm.call("account.move", "fetch_BP", [""]);
    const partnerSelect = this.rootRef.el.querySelector("#partner_2307");
    if (partnerSelect) {
      partnerSelect.innerHTML = construct_partners(data);
      this.state.selectedPartner = partnerSelect.value;
      await this.loadData();
    }
  }

  async onPrint2307() {
    const monthInput = this.rootRef.el.querySelector("#month_2307");
    const partnerSelect = this.rootRef.el.querySelector("#partner_2307");
    const current = monthInput ? monthInput.value : this.state.currentMonth;
    const BP = partnerSelect ? partnerSelect.value : this.state.selectedPartner;

    const data = await this.orm.call("account.move", "x_2307_forms", [
      "",
      { month: current, id: BP, trigger: "print", tranid: "none" },
    ]);
    this.action.doAction(data);
  }

  async onMonthKeypress(ev) {
    if (ev.which === 13) {
      await this.loadData();
    }
  }

  async onPartnerChange() {
    await this.loadData();
  }

  async loadData() {
    const monthInput = this.rootRef.el.querySelector("#month_2307");
    const partnerSelect = this.rootRef.el.querySelector("#partner_2307");
    const BP = partnerSelect ? partnerSelect.value : this.state.selectedPartner;
    const current = monthInput ? monthInput.value : this.state.currentMonth;

    const url =
      "/report/pdf/bir_module.form_2307/?id=" +
      BP +
      "&month=" +
      current +
      "&trigger=view";
    const previewFrame = this.rootRef.el.querySelector("#preview_2307");
    if (previewFrame) {
      previewFrame.src = url;
    }

    const data = await this.orm.call("account.move", "x_get_2307_data", [
      "",
      [[BP, current], "not_transactional", "table", "2307-Quarterly", "none"],
    ]);

    const ammendTable = this.rootRef.el.querySelector("#ammend_table_2307");
    if (ammendTable) {
      ammendTable.innerHTML = construct_ammendment_no_action(data);
      if (window.jQuery) {
        window.jQuery("#bir_ammend_table").DataTable();
        window.jQuery(".dataTables_length").addClass("bs-select");
      }
    }
  }
}

registry.category("actions").add("form_2307_page", Form2307);

// Form 2550M Component
export class Form2550M extends Component {
  static template = "bir_module.form_2550M_page";

  setup() {
    this.orm = useService("orm");
    this.action = useService("action");
    this.rootRef = useRef("root");

    this.state = useState({
      currentMonth: get_current(),
    });

    onMounted(async () => {
      await this.loadData();
    });
  }

  async onPrint2550M() {
    const monthInput = this.rootRef.el.querySelector("#month_2550M");
    const current = monthInput ? monthInput.value : this.state.currentMonth;

    const ids = [];
    const table = this.rootRef.el.querySelector("#bir_ammend_table");
    if (table) {
      const checkBoxes = table.getElementsByTagName("input");
      for (let i = 0; i < checkBoxes.length; i++) {
        if (!checkBoxes[i].checked) {
          const row = checkBoxes[i].parentNode.parentNode.parentNode;
          ids.push(row.cells.item(0).innerHTML);
        }
      }
    }

    const data = await this.orm.call("account.move", "x_2550_print_action", [
      "",
      { month: current, trans: "2550M", trigger: "exclude-print", ids: ids },
    ]);
    this.action.doAction(data);
    await this.loadData();
  }

  async onApply2550MExclude() {
    const monthInput = this.rootRef.el.querySelector("#month_2550M");
    const current = monthInput ? monthInput.value : this.state.currentMonth;

    const ids = [];
    const table = this.rootRef.el.querySelector("#bir_ammend_table");
    if (table) {
      const checkBoxes = table.getElementsByTagName("input");
      for (let i = 0; i < checkBoxes.length; i++) {
        if (!checkBoxes[i].checked) {
          const row = checkBoxes[i].parentNode.parentNode.parentNode;
          ids.push(row.cells.item(0).innerHTML);
        }
      }
    }

    const url =
      "/report/pdf/bir_module.form_2550M?month=" +
      current +
      "&trans=2550M&trigger=exclude-view&tranid=none&ids=" +
      encodeURIComponent(JSON.stringify(ids));
    const previewFrame = this.rootRef.el.querySelector("#preview_2550M");
    if (previewFrame) {
      previewFrame.src = url;
    }
  }

  async onMonthKeypress(ev) {
    if (ev.which === 13) {
      await this.loadData();
    }
  }

  async loadData() {
    const monthInput = this.rootRef.el.querySelector("#month_2550M");
    const current = monthInput ? monthInput.value : this.state.currentMonth;

    const url =
      "/report/pdf/bir_module.form_2550M?month=" +
      current +
      "&trans=2550M&trigger=view&tranid=none&ids=none";
    const previewFrame = this.rootRef.el.querySelector("#preview_2550M");
    if (previewFrame) {
      previewFrame.src = url;
    }

    const data = await this.orm.call(
      "account.move",
      "fetch_2550_table_docs_data",
      ["", [current, "2550M", "table"]]
    );

    const ammendTable = this.rootRef.el.querySelector("#ammend_table_2550M");
    if (ammendTable) {
      ammendTable.innerHTML = construct_ammendment(data);
      if (window.jQuery) {
        window.jQuery("#bir_ammend_table").DataTable();
        window.jQuery(".dataTables_length").addClass("bs-select");
      }
    }
  }
}

registry.category("actions").add("form_2550M_page", Form2550M);

// Form 2550Q Component
export class Form2550Q extends Component {
  static template = "bir_module.form_2550Q_page";

  setup() {
    this.orm = useService("orm");
    this.action = useService("action");
    this.rootRef = useRef("root");

    this.state = useState({
      currentMonth: get_current(),
    });

    onMounted(async () => {
      await this.loadData();
    });
  }

  async onPrint2550Q() {
    const monthInput = this.rootRef.el.querySelector("#month_2550Q");
    const current = monthInput ? monthInput.value : this.state.currentMonth;

    const data = await this.orm.call("account.move", "x_2550_print_action", [
      "",
      { month: current, trans: "2550Q", trigger: "print" },
    ]);
    this.action.doAction(data);
  }

  async onMonthKeypress(ev) {
    if (ev.which === 13) {
      await this.loadData();
    }
  }

  async loadData() {
    const monthInput = this.rootRef.el.querySelector("#month_2550Q");
    const current = monthInput ? monthInput.value : this.state.currentMonth;

    const url =
      "/report/pdf/bir_module.form_2550Q?month=" +
      current +
      "&trans=2550Q&trigger=view&tranid=none";
    const previewFrame = this.rootRef.el.querySelector("#preview_2550Q");
    if (previewFrame) {
      previewFrame.src = url;
    }

    const data = await this.orm.call(
      "account.move",
      "fetch_2550_table_docs_data",
      ["", [current, "2550Q", "table"]]
    );

    const ammendTable = this.rootRef.el.querySelector("#ammend_table_2550Q");
    if (ammendTable) {
      ammendTable.innerHTML = construct_ammendment_no_action(data);
      if (window.jQuery) {
        window.jQuery("#bir_ammend_table").DataTable();
        window.jQuery(".dataTables_length").addClass("bs-select");
      }
    }
  }
}

registry.category("actions").add("form_2550Q_page", Form2550Q);

// Form 1601E Component
export class Form1601E extends Component {
  static template = "bir_module.form_1601e_page";

  setup() {
    this.orm = useService("orm");
    this.action = useService("action");
    this.rootRef = useRef("root");

    this.state = useState({
      currentMonth: get_current(),
    });

    onMounted(() => {
      this.updatePreview();
    });
  }

  async onPrint1601e() {
    const monthInput = this.rootRef.el.querySelector("#month_1601e");
    const current = monthInput ? monthInput.value : this.state.currentMonth;

    const data = await this.orm.call("account.move", "x_1601e_print_action", [
      "",
      current,
    ]);
    this.action.doAction(data);
  }

  async onMonthKeypress(ev) {
    if (ev.which === 13) {
      this.updatePreview();
    }
  }

  updatePreview() {
    const monthInput = this.rootRef.el.querySelector("#month_1601e");
    const current = monthInput ? monthInput.value : this.state.currentMonth;
    const url = "/report/pdf/bir_module.form_1601e?month=" + current;
    const previewFrame = this.rootRef.el.querySelector("#preview_1601e");
    if (previewFrame) {
      previewFrame.src = url;
    }
  }
}

registry.category("actions").add("form_1601e_page", Form1601E);
