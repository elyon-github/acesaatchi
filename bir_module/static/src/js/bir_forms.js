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
/**
 * BIR Form 2307 - Certificate of Creditable Tax Withheld at Source
 * Handles the main form interface including:
 * - Partner selection with search
 * - Month/period selection
 * - Invoice record table with checkbox selection
 * - Real-time PDF preview with filtered data based on selected records
 * 
 * Checkbox Feature:
 * - When checkboxes are selected, ONLY those records are rendered in preview/print
 * - When NO checkboxes are selected, ALL records are rendered (default behavior)
 * - Selected IDs are passed via URL to the backend for SQL filtering
 */
export class Form2307 extends Component {
  static template = "bir_module.form_2307_page";

  setup() {
    this.orm = useService("orm");
    this.action = useService("action");
    this.rootRef = useRef("root");

    // Component state for managing form and UI
    this.state = useState({
      currentMonth: get_current(),
      selectedPartner: 0,
      partnersList: [],
      filteredPartners: [],
      searchTerm: "",
      checkedIds: new Set(), // Track which records are selected via checkboxes
    });

    onMounted(async () => {
      await this.loadInitialData();
      // Attach load listener to show/hide loading animation when preview updates
      this.attachPreviewLoadListener();
    });
  }

  async loadInitialData() {
    const data = await this.orm.call("account.move", "fetch_BP", [""]);
    this.state.partnersList = data;
    
    const partnerInput = this.rootRef.el.querySelector("#partner_2307");
    if (partnerInput && data.length > 0) {
      // Set first partner as default
      this.state.selectedPartner = data[0][0];
      partnerInput.value = data[0][1];
      
      // Add event listeners for dropdown
      partnerInput.addEventListener("input", () => this.onPartnerSearch());
      partnerInput.addEventListener("focus", () => this.showPartnerDropdown());
      document.addEventListener("click", (e) => this.handleClickOutside(e));
      
      await this.loadData();
    }
  }

  onPartnerSearch() {
    const input = this.rootRef.el.querySelector("#partner_2307");
    const searchTerm = (input.value || "").toLowerCase();
    
    if (searchTerm.length === 0) {
      this.state.filteredPartners = this.state.partnersList;
    } else {
      this.state.filteredPartners = this.state.partnersList.filter(partner => 
        partner[1].toLowerCase().includes(searchTerm) ||
        partner[0].toString().includes(searchTerm)
      );
    }
    
    this.showPartnerDropdown();
  }

  showPartnerDropdown() {
    const dropdown = this.rootRef.el.querySelector("#partner_2307_dropdown");
    if (!dropdown) return;

    const partners = this.state.filteredPartners;
    let html = "";
    
    if (partners.length === 0) {
      html = '<div class="bir-partner-option" style="color: #999; cursor: default;">No partners found</div>';
    } else {
      for (let partner of partners) {
        const isSelected = this.state.selectedPartner === partner[0];
        html += `<div class="bir-partner-option ${isSelected ? 'selected' : ''}" data-id="${partner[0]}" data-name="${partner[1]}">
          <span class="bir-partner-option-name">${partner[1]}</span>
          <span class="bir-partner-option-id">ID: ${partner[0]}</span>
        </div>`;
      }
    }

    dropdown.innerHTML = html;
    dropdown.classList.add("active");

    // Add click listeners to options
    const options = dropdown.querySelectorAll(".bir-partner-option[data-id]");
    options.forEach(option => {
      option.addEventListener("click", (e) => this.selectPartner(e));
    });
  }

  selectPartner(event) {
    const option = event.target.closest(".bir-partner-option");
    const partnerId = parseInt(option.dataset.id);
    const partnerName = option.dataset.name;

    this.state.selectedPartner = partnerId;
    this.state.searchTerm = ""; // Clear search when partner changes
    
    const input = this.rootRef.el.querySelector("#partner_2307");
    const idField = this.rootRef.el.querySelector("#partner_2307_id");
    const searchInput = this.rootRef.el.querySelector("#search_2307");
    
    input.value = partnerName;
    idField.value = partnerId;
    if (searchInput) {
      searchInput.value = "";
    }

    // Clear checked IDs when partner changes
    this.state.checkedIds = new Set();

    const dropdown = this.rootRef.el.querySelector("#partner_2307_dropdown");
    dropdown.classList.remove("active");

    this.loadData();
  }

  onSearchChange(ev) {
    this.state.searchTerm = ev.target.value;
    this.loadData();
  }

  handleClickOutside(event) {
    const input = this.rootRef.el?.querySelector("#partner_2307");
    const dropdown = this.rootRef.el?.querySelector("#partner_2307_dropdown");
    
    if (input && dropdown && !input.contains(event.target) && !dropdown.contains(event.target)) {
      dropdown.classList.remove("active");
    }
  }

  async onPrint2307() {
    const monthInput = this.rootRef.el.querySelector("#month_2307");
    const current = monthInput ? monthInput.value : this.state.currentMonth;
    const BP = this.state.selectedPartner;
    const search = this.state.searchTerm || "";
    const checkedIds = Array.from(this.state.checkedIds);

    const data = await this.orm.call("account.move", "x_2307_forms", [
      "",
      { month: current, id: BP, trigger: "print", tranid: "none", search: search, checked_ids: checkedIds },
    ]);
    this.action.doAction(data);
  }

  onMonthChange(ev) {
    // Update state with new month
    const monthInput = this.rootRef.el.querySelector("#month_2307");
    if (monthInput && monthInput.value) {
      this.state.currentMonth = monthInput.value.substring(0, 7);
    }
    
    this.state.searchTerm = ""; // Clear search when month changes
    this.state.checkedIds = new Set(); // Clear checked IDs when month changes
    const searchInput = this.rootRef.el.querySelector("#search_2307");
    if (searchInput) {
      searchInput.value = "";
    }
    this.loadData();
  }

  async loadData() {
    const monthInput = this.rootRef.el.querySelector("#month_2307");
    let current = this.state.currentMonth;
    
    if (monthInput && monthInput.value) {
      // Extract YYYY-MM from the date value (ignores the day)
      current = monthInput.value.substring(0, 7);
    }
    
    const BP = this.state.selectedPartner;
    const search = this.state.searchTerm || "";

    // Load table with ALL records (search filtered, but not checkbox filtered)
    // Checkboxes are for selecting which records to include in the PDF/preview
    const data = await this.orm.call("account.move", "x_get_2307_data", [
      "",
      [[BP, current], "not_transactional", "table", "2307-Quarterly", "none", search, []],
    ]);

    const ammendTable = this.rootRef.el.querySelector("#ammend_table_2307");
    if (ammendTable) {
      ammendTable.innerHTML = construct_ammendment_no_action(data);
      if (window.jQuery) {
        window.jQuery("#bir_ammend_table").DataTable({
          searching: false
        });
        window.jQuery(".dataTables_length").addClass("bs-select");
        // Move checkbox counter to the DataTables top controls
        this.moveCheckboxCounterToDataTables();
      }
      
      // Add event listeners for checkboxes (using event delegation)
      this.attachCheckboxEventDelegation();
      // Restore checkbox states from previous selections
      this.restoreCheckboxStates();
    }
    
    // Update preview with current selections after table is loaded
    this.updatePreviewOnly();
  }

  /**
   * Moves the checkbox counter to the DataTables top controls area
   * Places it on the same row as the "Show 10, 25, 50, 100" dropdown
   */
  moveCheckboxCounterToDataTables() {
    // Attempt multiple times to ensure DataTables is fully initialized
    let attempts = 0;
    const maxAttempts = 20;
    
    const injectCounter = () => {
      attempts++;
      const lengthControl = this.rootRef.el.querySelector(".dataTables_length");
      
      if (lengthControl && lengthControl.parentElement) {
        // Remove existing counter if it exists
        let counter = this.rootRef.el.querySelector("#checkbox_counter_2307");
        if (counter) {
          counter.remove();
        }
        
        // Create new counter element
        counter = document.createElement("span");
        counter.id = "checkbox_counter_2307";
        counter.className = "bir-checkbox-counter empty";
        counter.textContent = `Selections: 0`;
        counter.style.display = "inline-flex";
        
        // Insert right after the dataTables_length element
        lengthControl.parentElement.insertBefore(counter, lengthControl.nextSibling);
      } else if (attempts < maxAttempts) {
        // Retry if DataTables not ready yet
        setTimeout(injectCounter, 50);
      }
    };
    
    injectCounter();
  }

  /**
   * Attaches event delegation listener for checkbox changes
   * Uses event delegation so we don't need to re-attach when table is redrawn
   * Handles both individual checkboxes and "select all" checkbox
   */
  attachCheckboxEventDelegation() {
    const ammendTable = this.rootRef.el.querySelector("#ammend_table_2307");
    
    // Remove old delegation listener if it exists
    if (this._checkboxDelegationListener) {
      ammendTable.removeEventListener("change", this._checkboxDelegationListener);
    }
    
    // Create new delegation listener
    this._checkboxDelegationListener = (e) => {
      if (e.target.id === "select_all_2307") {
        // Select all checkbox
        this.handleSelectAllChange(e);
      } else if (e.target.classList.contains("bir-checkbox-2307")) {
        // Individual checkbox
        this.handleIndividualCheckboxChange(e);
      }
    };
    
    ammendTable.addEventListener("change", this._checkboxDelegationListener);
  }

  restoreCheckboxStates() {
    const itemCheckboxes = this.rootRef.el.querySelectorAll(".bir-checkbox-2307");
    const selectAllCheckbox = this.rootRef.el.querySelector("#select_all_2307");
    
    // Restore checkbox states from checkedIds
    itemCheckboxes.forEach(checkbox => {
      const moveId = parseInt(checkbox.dataset.moveId);
      checkbox.checked = this.state.checkedIds.has(moveId);
    });
    
    // Update select all checkbox state based on current selections
    if (selectAllCheckbox && itemCheckboxes.length > 0) {
      const allChecked = Array.from(itemCheckboxes).every(cb => cb.checked);
      const someChecked = Array.from(itemCheckboxes).some(cb => cb.checked);
      selectAllCheckbox.checked = allChecked;
      selectAllCheckbox.indeterminate = someChecked && !allChecked;
    }
    
    // Update checkbox counter display
    this.updateCheckboxCounter();
  }

  /**
   * Handles "select all" checkbox change
   * When checked: selects all visible records
   * When unchecked: clears all selections and reverts to showing all records
   */
  handleSelectAllChange(e) {
    const itemCheckboxes = this.rootRef.el.querySelectorAll(".bir-checkbox-2307");
    itemCheckboxes.forEach(checkbox => {
      checkbox.checked = e.target.checked;
      const moveId = parseInt(checkbox.dataset.moveId);
      if (e.target.checked) {
        this.state.checkedIds.add(moveId);
      } else {
        this.state.checkedIds.delete(moveId);
      }
    });
    // Update checkbox counter
    this.updateCheckboxCounter();
    // Update preview with current selections
    this.updatePreviewOnly();
  }

  handleIndividualCheckboxChange(e) {
    // Extract move ID from checkbox's data attribute
    const moveId = parseInt(e.target.dataset.moveId);
    
    // Add or remove from selected IDs set
    if (e.target.checked) {
      this.state.checkedIds.add(moveId);
    } else {
      this.state.checkedIds.delete(moveId);
    }
    
    // Update "select all" checkbox state based on current selections
    const itemCheckboxes = this.rootRef.el.querySelectorAll(".bir-checkbox-2307");
    const selectAllCheckbox = this.rootRef.el.querySelector("#select_all_2307");
    const allChecked = Array.from(itemCheckboxes).every(cb => cb.checked);
    const someChecked = Array.from(itemCheckboxes).some(cb => cb.checked);
    if (selectAllCheckbox) {
      selectAllCheckbox.checked = allChecked;
      selectAllCheckbox.indeterminate = someChecked && !allChecked;
    }
    
    // Update checkbox counter display
    this.updateCheckboxCounter();
    
    // Update preview with current selections
    this.updatePreviewOnly();
  }

  /**
   * Updates the checkbox counter display
   */
  updateCheckboxCounter() {
    const counter = this.rootRef.el.querySelector("#checkbox_counter_2307");
    if (!counter) return;
    
    const count = this.state.checkedIds.size;
    counter.textContent = `Selections: ${count}`;
    
    if (count === 0) {
      counter.classList.add("empty");
    } else {
      counter.classList.remove("empty");
    }
  }

  /**
   * Builds URL with current parameters and updates preview iframe with loading animation
   * Triggers when checkboxes are changed or search/month filters are modified
   */
  updatePreviewOnly() {
    // Get current month from input or use state default
    const monthInput = this.rootRef.el.querySelector("#month_2307");
    let current = this.state.currentMonth;
    
    if (monthInput && monthInput.value) {
      current = monthInput.value.substring(0, 7);
    }
    
    const BP = this.state.selectedPartner;
    const search = this.state.searchTerm || "";
    const checkedIds = Array.from(this.state.checkedIds);

    // Show loading animation before updating preview
    this.showPreviewLoading();

    // Build URL with all parameters using URLSearchParams for safe encoding
    const params = new URLSearchParams();
    params.append('id', BP);
    params.append('month', current);
    params.append('trigger', 'view');
    params.append('search', search);
    params.append('checked_ids', JSON.stringify(checkedIds));
    
    const url = "/report/pdf/bir_module.form_2307/?" + params.toString();
    
    // Update preview iframe source, which will trigger hiding the loading animation once loaded
    const previewFrame = this.rootRef.el.querySelector("#preview_2307");
    if (previewFrame) {
      previewFrame.src = url;
    }
  }

  /**
   * Shows loading spinner overlay on the preview iframe
   * Called before updating the preview to indicate data is being fetched
   */
  showPreviewLoading() {
    const previewContainer = this.rootRef.el.querySelector(".preview-container-2307");
    if (!previewContainer) return;

    // Create or show loading overlay
    let loader = previewContainer.querySelector(".preview-loader-2307");
    if (!loader) {
      loader = document.createElement("div");
      loader.className = "preview-loader-2307";
      loader.innerHTML = `
        <div class="loader-spinner">
          <div class="spinner"></div>
          <p>Generating preview...</p>
        </div>
      `;
      previewContainer.appendChild(loader);
    }
    loader.style.display = "flex";
  }

  /**
   * Hides the loading spinner overlay when preview finishes loading
   * Called when iframe load event is triggered
   */
  hidePreviewLoading() {
    const previewContainer = this.rootRef.el.querySelector(".preview-container-2307");
    if (!previewContainer) return;

    const loader = previewContainer.querySelector(".preview-loader-2307");
    if (loader) {
      loader.style.display = "none";
    }
  }

  /**
   * Attaches load event listener to preview iframe to hide loading animation when complete
   */
  attachPreviewLoadListener() {
    const previewFrame = this.rootRef.el.querySelector("#preview_2307");
    if (previewFrame) {
      previewFrame.addEventListener("load", () => {
        this.hidePreviewLoading();
      });
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

  onMonthChange(ev) {
    this.loadData();
  }

  async loadData() {
    const monthInput = this.rootRef.el.querySelector("#month_2550M");
    let current = this.state.currentMonth;
    
    if (monthInput && monthInput.value) {
      // Extract YYYY-MM from the date value (ignores the day)
      current = monthInput.value.substring(0, 7);
    }

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
    let current = this.state.currentMonth;
    
    if (monthInput && monthInput.value) {
      // Extract YYYY-MM from the date value (ignores the day)
      current = monthInput.value.substring(0, 7);
    }

    const data = await this.orm.call("account.move", "x_2550_print_action", [
      "",
      { month: current, trans: "2550Q", trigger: "print" },
    ]);
    this.action.doAction(data);
  }

  onMonthChange(ev) {
    this.loadData();
  }

  async loadData() {
    const monthInput = this.rootRef.el.querySelector("#month_2550Q");
    let current = this.state.currentMonth;
    
    if (monthInput && monthInput.value) {
      // Extract YYYY-MM from the date value (ignores the day)
      current = monthInput.value.substring(0, 7);
    }

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

  onMonthChange(ev) {
    this.updatePreview();
  }

  updatePreview() {
    const monthInput = this.rootRef.el.querySelector("#month_1601e");
    let current = this.state.currentMonth;
    
    if (monthInput && monthInput.value) {
      // Extract YYYY-MM from the date value (ignores the day)
      current = monthInput.value.substring(0, 7);
    }
    
    const url = "/report/pdf/bir_module.form_1601e?month=" + current;
    const previewFrame = this.rootRef.el.querySelector("#preview_1601e");
    if (previewFrame) {
      previewFrame.src = url;
    }
  }
}

registry.category("actions").add("form_1601e_page", Form1601E);
