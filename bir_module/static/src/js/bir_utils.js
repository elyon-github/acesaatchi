/** @odoo-module **/

// Utility Functions for BIR Module

export function get_current() {
  const now = new Date();
  const day = ("0" + now.getDate()).slice(-2);
  const month = ("0" + (now.getMonth() + 1)).slice(-2);
  const today = now.getFullYear() + "-" + month;
  return today;
}

export function numberWithCommas(x) {
  let str = 0;
  let num = 0;
  if (num != null) {
    num = parseFloat(x).toFixed(2);
    str = num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }
  return str;
}

export function format_vat(x) {
  let str = "None";
  if (x != null) {
    str = x.slice(0, 3) + "-" + x.slice(3, 6) + "-" + x.slice(6) + "-000";
  }
  return str;
}

export function construct_sawt(data) {
  let html =
    "<table class='table table-striped table-hover dt-responsive nowrap bir-data-table' id='sawt_datatable' role='table'><thead><tr>";

  html +=
    "<th scope='col'>No.</th>\
        <th scope='col'>Taxpayer ID (TIN)</th>\
        <th scope='col'>Corporation</th>\
        <th scope='col'>Bill Date</th>\
        <th scope='col'>Due Date</th>\
        <th scope='col'>Payment Status</th>\
        <th scope='col'>ATC Code</th>\
        <th scope='col' class='text-right'>Income Payment</th>\
        <th scope='col'>Tax Rate</th>\
        <th scope='col' class='text-right'>Tax Withheld</th></tr></thead><tbody>";

  let sub = 0;
  let tax = 0;
  let num = 1;
  for (let x in data) {
    let income = Math.abs(data[x][1]);
    let rate = Math.abs(data[x][5]);
    let amount = Math.abs(data[x][0]);
    let billDate = data[x][6] || "-";
    let dueDate = data[x][7] || "-";
    let paymentStatus = data[x][8] || "Unpaid";
    
    // Format dates if they exist
    if (billDate !== "-" && billDate) {
      billDate = new Date(billDate).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    }
    if (dueDate !== "-" && dueDate) {
      dueDate = new Date(dueDate).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    }
    
    // Payment status badge
    let statusBadge = 'bir-badge-warning';
    if (paymentStatus.toLowerCase() === 'paid') {
      statusBadge = 'bir-badge-success';
    } else if (paymentStatus.toLowerCase() === 'overdue') {
      statusBadge = 'bir-badge-danger';
    }

    html += "<tr>";
    html +=
      "<th scope='row'>" +
      num +
      "</td>\
            <td>" +
      data[x][2] +
      "</td>\
            <td>" +
      data[x][3] +
      "</td>\
            <td>" +
      billDate +
      "</td>\
            <td>" +
      dueDate +
      "</td>\
            <td><span class='bir-badge " +
      statusBadge +
      "'>" +
      paymentStatus +
      "</span></td>\
            <td>" +
      data[x][4] +
      "</td>\
            <td>" +
      numberWithCommas(income) +
      "</td>\
            <td>" +
      rate +
      "%</td>\
            <td>" +
      numberWithCommas(amount) +
      "</td>";
    html += "</tr>";

    sub += income;
    tax += amount;
    num += 1;
  }

  html +=
    "<tr>\
        <th scope='row'>" +
    (num + 1) +
    "</td>\
        <td></td><td></td><td></td><td></td><td></td><td></td>\
        <td scope='row'>" +
    numberWithCommas(sub) +
    "</td>\
        <td></td>\
        <td scope='row'>" +
    numberWithCommas(tax) +
    "</td>\
        </tr>";

  html += "</tbody></table>";
  return html;
}

export function construct_partners(data) {
  let html = "";
  for (let x in data) {
    html += "<option value='" + data[x][0] + "'>" + data[x][1] + "</option>";
  }
  return html;
}

export function construct_slp(data) {
  let html =
    "<table class='table table-striped table-hover dt-responsive nowrap bir-data-table' id='slp_datatable' role='table'><thead><tr>";

  html +=
    "<th scope='col'>Taxable Month</th>\
        <th scope='col'>Taxpayer ID (TIN)</th>\
        <th scope='col'>Registered Name</th>\
        <th scope='col' class='text-right'>Gross Purchase</th>\
        <th scope='col' class='text-right'>Exempt</th>\
        <th scope='col' class='text-right'>Zero-Rated</th>\
        <th scope='col' class='text-right'>Taxable</th>\
        <th scope='col' class='text-right'>Services</th>\
        <th scope='col' class='text-right'>Capital Goods</th>\
        <th scope='col' class='text-right'>Other Goods</th>\
        <th scope='col' class='text-right'>VAT</th>\
        <th scope='col' class='text-right'>Gross Tax</th></tr></thead><tbody>";

  let gross_sales_po_tot = 0;
  let excempt_tot = 0;
  let zero_rated_tot = 0;
  let taxable_tot = 0;
  let po_services_tot = 0;
  let po_capital_goods_tot = 0;
  let po_other_tot = 0;
  let tax_tot = 0;
  let gross_tax_tot = 0;

  let x;
  for (let y in data) {
    x = JSON.parse(JSON.stringify(data[y]));

    html += "<tr>";
    html +=
      "<th scope='row'></td>\
            <td>" +
      format_vat(x.vat) +
      "</td>\
            <td>" +
      x.name +
      "</td>\
            <td>" +
      numberWithCommas(x.gross_sales_po) +
      "</td>\
            <td>" +
      numberWithCommas(x.exempt) +
      "</td>\
            <td>" +
      numberWithCommas(x.zero_rated) +
      "</td>\
            <td>" +
      numberWithCommas(x.taxable) +
      "</td>\
            <td>" +
      numberWithCommas(x.po_services) +
      "</td>\
            <td>" +
      numberWithCommas(x.po_capital_goods) +
      "</td>\
            <td>" +
      numberWithCommas(x.po_other) +
      "</td>\
            <td>" +
      numberWithCommas(x.tax) +
      "</td>\
            <td>" +
      numberWithCommas(x.gross_tax) +
      "</td>";
    html += "</tr>";

    gross_sales_po_tot += x.gross_sales_po;
    excempt_tot += x.exempt;
    zero_rated_tot += x.zero_rated;
    taxable_tot += x.taxable;
    po_services_tot += x.po_services;
    po_capital_goods_tot += x.po_capital_goods;
    po_other_tot += x.po_other;
    tax_tot += x.tax;
    gross_tax_tot += x.gross_tax;
  }

  html +=
    "<tr><th scope='row'></td><td></td><td></td>\
        <td>" +
    numberWithCommas(gross_sales_po_tot) +
    "</td>\
        <td>" +
    numberWithCommas(excempt_tot) +
    "</td>\
        <td>" +
    numberWithCommas(zero_rated_tot) +
    "</td>\
        <td>" +
    numberWithCommas(taxable_tot) +
    "</td>\
        <td>" +
    numberWithCommas(po_services_tot) +
    "</td>\
        <td>" +
    numberWithCommas(po_capital_goods_tot) +
    "</td>\
        <td>" +
    numberWithCommas(po_other_tot) +
    "</td>\
        <td>" +
    numberWithCommas(tax_tot) +
    "</td>\
        <td>" +
    numberWithCommas(gross_tax_tot) +
    "</td></tr>";

  html += "</tbody></table>";
  return html;
}

export function construct_sls(data) {
  let html =
    "<table class='table table-striped table-hover dt-responsive nowrap bir-data-table' id='sls_datatable' role='table'><thead><tr>";

  html +=
    "<th scope='col'>Taxable Month</th>\
        <th scope='col'>Taxpayer ID (TIN)</th>\
        <th scope='col'>Registered Name</th>\
        <th scope='col' class='text-right'>Gross Purchase</th>\
        <th scope='col' class='text-right'>Exempt</th>\
        <th scope='col' class='text-right'>Zero-Rated</th>\
        <th scope='col' class='text-right'>Taxable</th>\
        <th scope='col' class='text-right'>VAT</th>\
        <th scope='col' class='text-right'>Gross Tax</th></tr></thead><tbody>";

  let gross_sales_po_tot = 0;
  let excempt_tot = 0;
  let zero_rated_tot = 0;
  let taxable_tot = 0;
  let tax_tot = 0;
  let gross_tax_tot = 0;
  let x;
  for (let y in data) {
    x = JSON.parse(JSON.stringify(data[y]));

    html += "<tr>";
    html +=
      "<th scope='row'></td>\
            <td>" +
      format_vat(x.vat) +
      "</td>\
            <td>" +
      x.name +
      "</td>\
            <td>" +
      numberWithCommas(x.gross_sales_po) +
      "</td>\
            <td>" +
      numberWithCommas(x.exempt) +
      "</td>\
            <td>" +
      numberWithCommas(x.zero_rated) +
      "</td>\
            <td>" +
      numberWithCommas(x.taxable) +
      "</td>\
            <td>" +
      numberWithCommas(x.tax) +
      "</td>\
            <td>" +
      numberWithCommas(x.gross_tax) +
      "</td>";
    html += "</tr>";

    gross_sales_po_tot += x.gross_sales_po;
    excempt_tot += x.exempt;
    zero_rated_tot += x.zero_rated;
    taxable_tot += x.taxable;
    tax_tot += x.tax;
    gross_tax_tot += x.gross_tax;
  }

  html +=
    "<tr><th scope='row'></td><td></td><td></td>\
        <td>" +
    numberWithCommas(gross_sales_po_tot) +
    "</td>\
        <td>" +
    numberWithCommas(excempt_tot) +
    "</td>\
        <td>" +
    numberWithCommas(zero_rated_tot) +
    "</td>\
        <td>" +
    numberWithCommas(taxable_tot) +
    "</td>\
        <td>" +
    numberWithCommas(tax_tot) +
    "</td>\
        <td>" +
    numberWithCommas(gross_tax_tot) +
    "</td>\
        </tr>";

  html += "</tbody></table>";
  return html;
}

export function construct_print_types(data) {
  let html = "<option value='all'>All</option>";
  for (let x in data) {
    html += "<option value='" + data[x][0] + "'>" + data[x][0] + "</option>";
  }
  return html;
}

export function construct_print_history(data, component) {
  let html =
    "<table class='table table-striped table-hover dt-responsive nowrap bir-data-table' id='print_history_datatable' role='table'><thead><tr>";

  html +=
    "<th scope='col'>ID</th>\
        <th scope='col'>Form Type</th>\
        <th scope='col'>Print Date</th>\
        <th scope='col'>User</th>\
        <th scope='col'>Action</th></tr></thead><tbody>";

  for (let y in data) {
    html +=
      "<tr><td class='print_id_val fw-bold'>" +
      data[y][0] +
      "</td>\
            <td><span class='bir-badge bir-badge-info'>" +
      data[y][1] +
      "</span></td>\
            <td>" +
      data[y][2] +
      "</td>\
            <td>" +
      data[y][3] +
      "</td>\
            <td class='bir-table-actions'>\
            <button class='btn btn-sm btn-info print_details_btn' value='" +
      data[y][0] +
      "' data-bs-toggle='modal' data-bs-target='#print_details_modal' title='View Details'><i class='fa fa-eye'></i> Details</button>\
            <button class='btn btn-sm btn-primary preview_details_btn' value='" +
      data[y][0] +
      "' data-bs-toggle='modal' data-bs-target='#print_preview_modal' title='Preview'><i class='fa fa-print'></i> Preview</button>\
            </td></tr>";
  }

  html += "</tbody></table>";

  // Add event listeners for dynamically created buttons
  setTimeout(() => {
    if (component && component.rootRef.el) {
      const detailBtns =
        component.rootRef.el.querySelectorAll(".print_details_btn");
      const previewBtns = component.rootRef.el.querySelectorAll(
        ".preview_details_btn"
      );

      detailBtns.forEach((btn) => {
        btn.addEventListener("click", (e) => component.onPrintDetailsClick(e));
      });

      previewBtns.forEach((btn) => {
        btn.addEventListener("click", (e) =>
          component.onPreviewDetailsClick(e)
        );
      });
    }
  }, 100);

  return html;
}

export function construct_print_details(data) {
  let html =
    "<table class='table table-striped table-hover dt-responsive nowrap bir-data-table' id='print_history_line_datatable' role='table'><thead><tr>";

  html +=
    "<th scope='col'>Document Code</th>\
        <th scope='col'>Type</th>\
        </tr></thead><tbody>";

  for (let y in data) {
    let scope = "Vendor Bill";
    let badgeClass = "bir-badge-warning";
    if (data[y][2] == "out_invoice") {
      scope = "Customer Invoice";
      badgeClass = "bir-badge-success";
    }
    html +=
      "<tr>\
            <td class='fw-bold'>" +
      data[y][1] +
      "</td>\
            <td><span class='bir-badge " + badgeClass + "'>" +
      scope +
      "</span></td></tr>";
  }
  html += "</tbody></table>";
  return html;
}

export function construct_ammendment_no_action(data) {
  // Renders HTML table with checkboxes for selecting records
  // Used in BIR 2307 form for selecting which invoices to include in the form
  // Each row has a checkbox with data-move-id attribute containing the invoice ID
  
  let html =
    "<table class='table table-striped table-hover dt-responsive nowrap bir-data-table' id='bir_ammend_table' role='table'><thead><tr>";

  html +=
    "<th scope='col' style='width: 40px;'><input type='checkbox' id='select_all_2307' class='form-check-input' title='Select all'/></th>\
        <th scope='col'>Name</th>\
        <th scope='col'>Type</th>\
        <th scope='col'>Bill Date</th>\
        <th scope='col'>Due Date</th>\
        <th scope='col'>Payment Status</th>\
        <th scope='col' class='text-right'>Untaxed Amount</th>\
        <th scope='col' class='text-right'>Total Amount</th>\
        </tr></thead><tbody>";

  for (let y in data) {
    let scope = "Vendor Bill";
    let badgeClass = "bir-badge-warning";
    if (data[y][2] == "out_invoice") {
      scope = "Customer Invoice";
      badgeClass = "bir-badge-success";
    }
    
    let billDate = data[y][5] || "-";
    let dueDate = data[y][6] || "-";
    let paymentStatus = data[y][7] || "Unpaid";
    let moveId = data[y][0] || ""; // Move ID is at index 0 from process_2307_ammend()
    
    // Format dates if they exist
    if (billDate !== "-" && billDate) {
      billDate = new Date(billDate).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    }
    if (dueDate !== "-" && dueDate) {
      dueDate = new Date(dueDate).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    }
    
    // Payment status badge styling
    let statusBadge = 'bir-badge-warning';
    if (paymentStatus.toLowerCase() === 'paid') {
      statusBadge = 'bir-badge-success';
    } else if (paymentStatus.toLowerCase() === 'overdue') {
      statusBadge = 'bir-badge-danger';
    }
    
    html +=
      "<tr>\
            <td style='width: 40px;'><input type='checkbox' class='form-check-input bir-checkbox-2307' data-move-id='" + moveId + "'/></td>\
            <td>" +
      data[y][1] +
      "</td>\
            <td><span class='bir-badge " + badgeClass + "'>" +
      scope +
      "</span></td>\
            <td>" +
      billDate +
      "</td>\
            <td>" +
      dueDate +
      "</td>\
            <td><span class='bir-badge " +
      statusBadge +
      "'>" +
      paymentStatus +
      "</span></td>\
            <td class='text-right'>" +
      numberWithCommas(data[y][3]) +
      "</td>\
            <td class='text-right'>" +
      numberWithCommas(data[y][4]) +
      "</td></tr>";
  }

  html += "</tbody></table>";
  return html;
}

export function construct_ammendment(data) {
  let html =
    "<table class='table table-striped table-hover dt-responsive nowrap bir-data-table' id='bir_ammend_table' role='table'><thead><tr>";

  html +=
    "<th scope='col'>ID</th>\
        <th scope='col'>Name</th>\
        <th scope='col'>Type</th>\
        <th scope='col' class='text-right'>Total Amount</th>\
        <th scope='col' class='text-center'>Exclude</th>\
        </tr></thead><tbody>";

  for (let y in data) {
    let scope = "Vendor Bill";
    let badgeClass = "bir-badge-warning";
    if (data[y][2] == "out_invoice") {
      scope = "Customer Invoice";
      badgeClass = "bir-badge-success";
    }
    html +=
      "<tr>\
            <td class='fw-bold'>" +
      data[y][0] +
      "</td>\
            <td>" +
      data[y][1] +
      "</td>\
            <td><span class='bir-badge " + badgeClass + "'>" +
      scope +
      "</span></td>\
            <td class='text-right'>" +
      numberWithCommas(data[y][3]) +
      "</td>\
            <td class='bir-table-checkbox text-center'><input type='checkbox' class='form-check-input bir-checkbox' id='ammend-check-" + data[y][0] + "' aria-label='Exclude document' /></td></tr>";
  }

  html += "</tbody></table>";
  return html;
}
