/**
 * SCM2 Django REST API — TypeScript type definitions
 *
 * Generated from Django model definitions across all SCM2 modules.
 * Field nullability mirrors the Django model: fields with `null=True` or
 * `blank=True` are typed as `string | null` / `number | null` where
 * appropriate, and exposed as optional (`?`) on Create/Update types.
 *
 * Decimal fields (Django DecimalField) are represented as `string` because
 * Django REST Framework serialises them as fixed-point strings (e.g. "1234.56")
 * to preserve precision. Cast to `number` at the use-site only when arithmetic
 * is needed.
 *
 * Date strings follow ISO-8601: DateField → "YYYY-MM-DD",
 * DateTimeField → "YYYY-MM-DDTHH:mm:ss[.ffffff]Z".
 */

// ---------------------------------------------------------------------------
// Shared / utility types
// ---------------------------------------------------------------------------

/** Wraps any paginated DRF list endpoint (PageNumberPagination). */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Standard DRF error shape. Field errors carry string[] per field name. */
export interface ApiError {
  detail?: string;
  non_field_errors?: string[];
  [field: string]: string | string[] | undefined;
}

// ---------------------------------------------------------------------------
// scm_accounts — Company / User
// ---------------------------------------------------------------------------

export type CompanyPlan = "BASIC" | "STANDARD" | "ENTERPRISE";

export interface Company {
  id: number;
  company_code: string;
  company_name: string;
  business_no: string;
  plan: CompanyPlan;
  is_active: boolean;
  created_at: string;
}

export interface CreateCompany {
  company_code: string;
  company_name: string;
  business_no?: string;
  plan?: CompanyPlan;
  is_active?: boolean;
}

export type UpdateCompany = Partial<CreateCompany>;

export interface User {
  id: number;
  email: string;
  username: string;
  name: string;
  department: string;
  is_admin: boolean;
  company: number | null;
}

export interface UserPermission {
  id: number;
  user: number;
  module: string;
  can_read: boolean;
  can_write: boolean;
}

// ---------------------------------------------------------------------------
// MM — Material Management
// ---------------------------------------------------------------------------

export type PurchaseOrderStatus = "발주확정" | "납품중" | "입고완료" | "취소";

export interface Supplier {
  id: number;
  company: number | null;
  name: string;
  contact: string;
  email: string;
  phone: string;
  payment_terms: string;
  status: string;
  created_at: string;
}

export interface CreateSupplier {
  name: string;
  contact?: string;
  email?: string;
  phone?: string;
  payment_terms?: string;
  status?: string;
}

export type UpdateSupplier = Partial<CreateSupplier>;

export interface Material {
  id: number;
  company: number | null;
  material_code: string;
  material_name: string;
  material_type: string;
  unit: string;
  min_stock: number;
  lead_time_days: number;
  created_at: string;
}

export interface CreateMaterial {
  material_code: string;
  material_name: string;
  material_type?: string;
  unit?: string;
  min_stock?: number;
  lead_time_days?: number;
}

export type UpdateMaterial = Partial<CreateMaterial>;

export interface PurchaseOrder {
  id: number;
  company: number | null;
  po_number: string;
  supplier: number | null;
  /** Read-only computed field included by the serializer. */
  supplier_name?: string;
  item_name: string;
  quantity: number;
  unit_price: string;
  currency: string;
  delivery_date: string | null;
  warehouse: string;
  status: PurchaseOrderStatus;
  note: string;
  created_at: string;
  /** Read-only computed total returned by the serializer. */
  total_amount?: number;
}

export interface CreatePurchaseOrder {
  po_number: string;
  supplier?: number | null;
  item_name: string;
  quantity: number;
  unit_price: string;
  currency?: string;
  delivery_date?: string | null;
  warehouse?: string;
  status?: PurchaseOrderStatus;
  note?: string;
}

export type UpdatePurchaseOrder = Partial<CreatePurchaseOrder>;

export interface GoodsReceipt {
  id: number;
  company: number | null;
  gr_number: string;
  po: number | null;
  /** Read-only computed field included by the serializer. */
  po_number?: string;
  item_name: string;
  ordered_qty: number;
  received_qty: number;
  rejected_qty: number;
  warehouse: string;
  receiver: string;
  created_at: string;
}

export interface CreateGoodsReceipt {
  gr_number: string;
  po?: number | null;
  item_name: string;
  ordered_qty: number;
  received_qty: number;
  rejected_qty?: number;
  warehouse?: string;
  receiver?: string;
}

export type UpdateGoodsReceipt = Partial<CreateGoodsReceipt>;

export type RfqStatus = "draft" | "sent" | "received" | "closed";

export interface RFQ {
  id: number;
  company: number;
  rfq_number: string;
  supplier: number | null;
  item_name: string;
  quantity: number;
  required_date: string | null;
  status: RfqStatus;
  note: string;
  created_at: string;
}

export interface CreateRFQ {
  rfq_number: string;
  supplier?: number | null;
  item_name: string;
  quantity: number;
  required_date?: string | null;
  status?: RfqStatus;
  note?: string;
}

export type UpdateRFQ = Partial<CreateRFQ>;

export interface SupplierEvaluation {
  id: number;
  company: number;
  supplier: number;
  eval_year: number;
  eval_month: number;
  delivery_score: string;
  quality_score: string;
  price_score: string;
  total_score: string;
  grade: string;
  note: string;
  created_at: string;
}

export interface CreateSupplierEvaluation {
  supplier: number;
  eval_year: number;
  eval_month: number;
  delivery_score?: string;
  quality_score?: string;
  price_score?: string;
  total_score?: string;
  grade?: string;
  note?: string;
}

export type UpdateSupplierEvaluation = Partial<CreateSupplierEvaluation>;

// ---------------------------------------------------------------------------
// SD — Sales & Distribution
// ---------------------------------------------------------------------------

export type SalesOrderStatus =
  | "주문접수"
  | "생산/조달중"
  | "출하준비"
  | "배송중"
  | "배송완료"
  | "취소";

export interface Customer {
  id: number;
  company: number | null;
  customer_code: string;
  customer_name: string;
  contact: string;
  email: string;
  credit_limit: string;
  payment_terms: string;
  status: string;
  created_at: string;
}

export interface CreateCustomer {
  customer_code: string;
  customer_name: string;
  contact?: string;
  email?: string;
  credit_limit?: string;
  payment_terms?: string;
  status?: string;
}

export type UpdateCustomer = Partial<CreateCustomer>;

export interface SalesOrderLine {
  id: number;
  order: number;
  line_no: number;
  item_name: string;
  quantity: number;
  unit_price: string;
  discount_rate: string;
  amount: string;
  delivery_date: string | null;
  note: string;
}

export interface CreateSalesOrderLine {
  line_no?: number;
  item_name: string;
  quantity: number;
  unit_price: string;
  discount_rate?: string;
  amount?: string;
  delivery_date?: string | null;
  note?: string;
}

export type UpdateSalesOrderLine = Partial<CreateSalesOrderLine>;

export interface SalesOrder {
  id: number;
  company: number | null;
  order_number: string;
  customer: number | null;
  customer_name: string;
  item_name: string;
  quantity: number;
  unit_price: string;
  discount_rate: string;
  status: SalesOrderStatus;
  shipped_qty: number;
  ordered_at: string;
  /** Read-only computed property from the Django model. */
  total_amount?: number;
  /** Nested lines are included when the serializer uses depth or explicit nesting. */
  lines?: SalesOrderLine[];
}

export interface CreateSalesOrder {
  order_number: string;
  customer?: number | null;
  customer_name: string;
  item_name: string;
  quantity: number;
  unit_price: string;
  discount_rate?: string;
  status?: SalesOrderStatus;
  shipped_qty?: number;
  lines?: CreateSalesOrderLine[];
}

export type UpdateSalesOrder = Partial<CreateSalesOrder>;

export interface Delivery {
  id: number;
  company: number | null;
  delivery_number: string;
  order: number | null;
  item_name: string;
  delivery_qty: number;
  carrier: string;
  tracking_number: string;
  delivery_date: string | null;
  status: string;
  created_at: string;
}

export interface CreateDelivery {
  delivery_number: string;
  order?: number | null;
  item_name: string;
  delivery_qty: number;
  carrier?: string;
  tracking_number?: string;
  delivery_date?: string | null;
  status?: string;
}

export type UpdateDelivery = Partial<CreateDelivery>;

export interface CustomerCreditHistory {
  id: number;
  company: number;
  customer: number;
  transaction_date: string;
  amount: string;
  balance: string;
  note: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// WM — Warehouse Management
// ---------------------------------------------------------------------------

export type StockMovementType = "IN" | "OUT" | "TRANSFER" | "ADJUST";
export type StockMovementReferenceType = "PO" | "SO" | "WO";

export interface Warehouse {
  id: number;
  company: number | null;
  warehouse_code: string;
  warehouse_name: string;
  warehouse_type: string;
  location: string;
  is_active: boolean;
}

export interface CreateWarehouse {
  warehouse_code: string;
  warehouse_name: string;
  warehouse_type?: string;
  location?: string;
  is_active?: boolean;
}

export type UpdateWarehouse = Partial<CreateWarehouse>;

export interface Inventory {
  id: number;
  company: number | null;
  item_code: string;
  item_name: string;
  category: string;
  warehouse: number | null;
  /** Read-only denormalised name included by the serializer. */
  warehouse_name?: string;
  bin_code: string;
  stock_qty: number;
  system_qty: number;
  unit_price: string;
  min_stock: number;
  expiry_date: string | null;
  lot_number: string;
  updated_at: string;
  /** Read-only computed property from the Django model. */
  is_low_stock?: boolean;
}

export interface CreateInventory {
  item_code: string;
  item_name: string;
  category?: string;
  warehouse?: number | null;
  bin_code?: string;
  stock_qty?: number;
  system_qty?: number;
  unit_price?: string;
  min_stock?: number;
  expiry_date?: string | null;
  lot_number?: string;
}

export type UpdateInventory = Partial<CreateInventory>;

/** StockMovement is a read-only audit log — no Create/Update types provided. */
export interface StockMovement {
  id: number;
  company: number | null;
  warehouse: number | null;
  /** Read-only denormalised name included by the serializer. */
  warehouse_name?: string;
  material_code: string;
  material_name: string;
  movement_type: StockMovementType;
  /** Read-only display label for movement_type. */
  movement_type_display?: string;
  quantity: string;
  before_qty: string;
  after_qty: string;
  reference_document: string;
  reference_type: StockMovementReferenceType | "";
  /** Read-only display label for reference_type. */
  reference_type_display?: string;
  note: string;
  created_at: string;
  created_by: string;
}

export interface BinLocation {
  id: number;
  company: number;
  warehouse: number;
  bin_code: string;
  aisle: string;
  row: string;
  level: string;
  capacity: string;
  is_active: boolean;
}

export interface CreateBinLocation {
  warehouse: number;
  bin_code: string;
  aisle?: string;
  row?: string;
  level?: string;
  capacity?: string;
  is_active?: boolean;
}

export type UpdateBinLocation = Partial<CreateBinLocation>;

export type CycleCountStatus = "draft" | "in_progress" | "completed" | "cancelled";

export interface CycleCount {
  id: number;
  company: number;
  count_number: string;
  warehouse: number | null;
  count_date: string;
  status: CycleCountStatus;
  counter: string;
  note: string;
  created_at: string;
}

export interface CycleCountLine {
  id: number;
  cycle_count: number;
  inventory: number;
  system_qty: string;
  counted_qty: string | null;
  variance: string | null;
  note: string;
}

// ---------------------------------------------------------------------------
// PP — Production Planning
// ---------------------------------------------------------------------------

export type ProductionOrderStatus = "계획" | "확정" | "생산중" | "완료" | "취소";
export type MrpRunStatus = "실행중" | "완료" | "오류";

export interface BillOfMaterial {
  id: number;
  company: number | null;
  bom_code: string;
  product_name: string;
  version: string;
  is_active: boolean;
  created_at: string;
  /** Nested lines are included when the serializer uses depth or explicit nesting. */
  lines?: BomLine[];
}

export interface CreateBillOfMaterial {
  bom_code: string;
  product_name: string;
  version?: string;
  is_active?: boolean;
  lines?: CreateBomLine[];
}

export type UpdateBillOfMaterial = Partial<CreateBillOfMaterial>;

export interface BomLine {
  id: number;
  bom: number;
  material_code: string;
  material_name: string;
  quantity: string;
  unit: string;
  scrap_rate: string;
}

export interface CreateBomLine {
  material_code: string;
  material_name: string;
  quantity: string;
  unit?: string;
  scrap_rate?: string;
}

export type UpdateBomLine = Partial<CreateBomLine>;

export interface ProductionOrder {
  id: number;
  company: number | null;
  order_number: string;
  bom: number | null;
  product_name: string;
  planned_qty: number;
  produced_qty: number;
  defect_qty: number;
  status: ProductionOrderStatus;
  planned_start: string | null;
  planned_end: string | null;
  actual_start: string | null;
  actual_end: string | null;
  work_center: string;
  note: string;
  created_at: string;
  /** Read-only computed property from the Django model. */
  completion_rate?: number;
}

export interface CreateProductionOrder {
  order_number: string;
  bom?: number | null;
  product_name: string;
  planned_qty: number;
  produced_qty?: number;
  defect_qty?: number;
  status?: ProductionOrderStatus;
  planned_start?: string | null;
  planned_end?: string | null;
  actual_start?: string | null;
  actual_end?: string | null;
  work_center?: string;
  note?: string;
}

export type UpdateProductionOrder = Partial<CreateProductionOrder>;

export interface MrpRun {
  id: number;
  company: number | null;
  run_number: string;
  run_date: string;
  status: MrpRunStatus;
  total_items: number;
  planned_orders: number;
  note: string;
}

export interface CreateMrpRun {
  run_number: string;
  status?: MrpRunStatus;
  total_items?: number;
  planned_orders?: number;
  note?: string;
}

export type UpdateMrpRun = Partial<CreateMrpRun>;

// ---------------------------------------------------------------------------
// HR — Human Resources
// ---------------------------------------------------------------------------

export type EmployeeStatus = "재직" | "퇴직" | "휴직";
export type EmploymentType = "정규직" | "계약직" | "파견직" | "인턴";
export type AttendanceWorkType =
  | "normal"
  | "late"
  | "early"
  | "absent"
  | "holiday"
  | "overtime";
export type LeaveType = "annual" | "half" | "sick" | "special" | "unpaid";
export type LeaveStatus = "pending" | "approved" | "rejected" | "cancelled";
export type PayrollState = "DRAFT" | "확정";

export interface Department {
  id: number;
  company: number | null;
  dept_code: string;
  dept_name: string;
  is_active: boolean;
}

export interface CreateDepartment {
  dept_code: string;
  dept_name: string;
  is_active?: boolean;
}

export type UpdateDepartment = Partial<CreateDepartment>;

export interface Employee {
  id: number;
  company: number | null;
  emp_code: string;
  name: string;
  dept: number | null;
  position: string;
  employment_type: EmploymentType;
  hire_date: string;
  resign_date: string | null;
  status: EmployeeStatus;
  email: string;
  phone: string;
  base_salary: string;
  created_at: string;
}

export interface CreateEmployee {
  emp_code: string;
  name: string;
  dept?: number | null;
  position?: string;
  employment_type?: EmploymentType;
  hire_date: string;
  resign_date?: string | null;
  status?: EmployeeStatus;
  email?: string;
  phone?: string;
  base_salary?: string;
}

export type UpdateEmployee = Partial<CreateEmployee>;

export interface Payroll {
  id: number;
  company: number | null;
  payroll_number: string;
  employee: number;
  pay_year: number;
  pay_month: number;
  base_salary: string;
  overtime_pay: string;
  bonus: string;
  gross_pay: string;
  national_pension: string;
  health_insurance: string;
  employment_insurance: string;
  income_tax: string;
  total_deduction: string;
  net_pay: string;
  state: PayrollState;
  payment_date: string | null;
  created_at: string;
}

export interface CreatePayroll {
  payroll_number: string;
  employee: number;
  pay_year: number;
  pay_month: number;
  base_salary: string;
  overtime_pay?: string;
  bonus?: string;
  gross_pay: string;
  national_pension?: string;
  health_insurance?: string;
  employment_insurance?: string;
  income_tax?: string;
  total_deduction?: string;
  net_pay: string;
  state?: PayrollState;
  payment_date?: string | null;
}

export type UpdatePayroll = Partial<CreatePayroll>;

export interface Attendance {
  id: number;
  company: number;
  employee: number;
  work_date: string;
  check_in: string | null;
  check_out: string | null;
  work_type: AttendanceWorkType;
  overtime_hours: string;
  note: string;
}

export interface CreateAttendance {
  employee: number;
  work_date: string;
  check_in?: string | null;
  check_out?: string | null;
  work_type?: AttendanceWorkType;
  overtime_hours?: string;
  note?: string;
}

export type UpdateAttendance = Partial<CreateAttendance>;

export interface Leave {
  id: number;
  company: number;
  employee: number;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  days: string;
  reason: string;
  status: LeaveStatus;
  approved_by: number | null;
  created_at: string;
}

export interface CreateLeave {
  employee: number;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  days: string;
  reason?: string;
  status?: LeaveStatus;
}

export type UpdateLeave = Partial<CreateLeave>;

export interface LeaveBalance {
  id: number;
  company: number;
  employee: number;
  year: number;
  total_days: string;
  used_days: string;
  remaining_days: string;
}

// ---------------------------------------------------------------------------
// FI — Finance
// ---------------------------------------------------------------------------

export type AccountType =
  | "ASSET"
  | "LIABILITY"
  | "EQUITY"
  | "REVENUE"
  | "EXPENSE";
export type AccountMoveState = "DRAFT" | "POSTED" | "CANCELLED";
export type AccountMoveType =
  | "ENTRY"
  | "PURCHASE"
  | "SALE"
  | "PAYMENT"
  | "RECEIPT"
  | "ADJUST";
export type FixedAssetCategory =
  | "machinery"
  | "vehicle"
  | "equipment"
  | "furniture"
  | "intangible";
export type FixedAssetDepreciationMethod = "straight_line" | "declining";
export type FixedAssetStatus = "active" | "disposed" | "retired";
export type TaxInvoiceType = "SALE" | "PURCHASE";
export type TaxInvoiceStatus = "draft" | "issued" | "cancelled";

export interface Account {
  id: number;
  company: number | null;
  code: string;
  name: string;
  account_type: AccountType;
  root_type: string;
  is_group: boolean;
  is_active: boolean;
}

export interface CreateAccount {
  code: string;
  name: string;
  account_type: AccountType;
  root_type?: string;
  is_group?: boolean;
  is_active?: boolean;
}

export type UpdateAccount = Partial<CreateAccount>;

export interface AccountMoveLine {
  id: number;
  move: number;
  account: number;
  name: string;
  debit: string;
  credit: string;
  is_reconciled: boolean;
  due_date: string | null;
}

export interface CreateAccountMoveLine {
  account: number;
  name?: string;
  debit?: string;
  credit?: string;
  due_date?: string | null;
}

export type UpdateAccountMoveLine = Partial<CreateAccountMoveLine>;

export interface AccountMove {
  id: number;
  company: number | null;
  move_number: string;
  move_type: AccountMoveType;
  posting_date: string;
  ref: string;
  state: AccountMoveState;
  total_debit: string;
  total_credit: string;
  created_by: string;
  created_at: string;
  posted_at: string | null;
  /** Nested lines are included when the serializer uses depth or explicit nesting. */
  lines?: AccountMoveLine[];
}

export interface CreateAccountMove {
  move_number: string;
  move_type: AccountMoveType;
  posting_date: string;
  ref?: string;
  state?: AccountMoveState;
  created_by?: string;
  lines?: CreateAccountMoveLine[];
}

export type UpdateAccountMove = Partial<CreateAccountMove>;

export interface Budget {
  id: number;
  company: number;
  budget_year: number;
  budget_month: number | null;
  account: number;
  budgeted_amount: string;
  actual_amount: string;
  variance: string;
  note: string;
}

export interface CreateBudget {
  budget_year: number;
  budget_month?: number | null;
  account: number;
  budgeted_amount?: string;
  actual_amount?: string;
  variance?: string;
  note?: string;
}

export type UpdateBudget = Partial<CreateBudget>;

export interface FixedAsset {
  id: number;
  company: number;
  asset_code: string;
  asset_name: string;
  category: FixedAssetCategory;
  acquisition_date: string;
  acquisition_cost: string;
  useful_life_years: number;
  salvage_value: string;
  depreciation_method: FixedAssetDepreciationMethod;
  accumulated_depreciation: string;
  book_value: string;
  status: FixedAssetStatus;
  location: string;
}

export interface CreateFixedAsset {
  asset_code: string;
  asset_name: string;
  category: FixedAssetCategory;
  acquisition_date: string;
  acquisition_cost: string;
  useful_life_years?: number;
  salvage_value?: string;
  depreciation_method?: FixedAssetDepreciationMethod;
  status?: FixedAssetStatus;
  location?: string;
}

export type UpdateFixedAsset = Partial<CreateFixedAsset>;

export interface DepreciationSchedule {
  id: number;
  asset: number;
  period_year: number;
  period_month: number;
  depreciation_amount: string;
  accumulated_amount: string;
  book_value_after: string;
  is_posted: boolean;
}

export interface TaxInvoice {
  id: number;
  company: number;
  invoice_number: string;
  invoice_type: TaxInvoiceType;
  issue_date: string;
  counterpart: string;
  supply_amount: string;
  vat_amount: string;
  total_amount: string;
  status: TaxInvoiceStatus;
  remark: string;
  created_at: string;
}

export interface CreateTaxInvoice {
  invoice_number: string;
  invoice_type?: TaxInvoiceType;
  issue_date: string;
  counterpart: string;
  supply_amount?: string;
  vat_amount?: string;
  total_amount?: string;
  status?: TaxInvoiceStatus;
  remark?: string;
}

export type UpdateTaxInvoice = Partial<CreateTaxInvoice>;

// ---------------------------------------------------------------------------
// QM — Quality Management
// ---------------------------------------------------------------------------

export type InspectionType = "수입검사" | "공정검사" | "출하검사" | "정기검사";
export type InspectionResultValue = "합격" | "불합격" | "조건부합격";
export type DefectSeverity = "경미" | "보통" | "심각" | "치명";
export type CorrectiveActionStatus =
  | "등록"
  | "조사중"
  | "이행중"
  | "완료"
  | "종결";

export interface InspectionPlan {
  id: number;
  company: number | null;
  plan_code: string;
  plan_name: string;
  inspection_type: InspectionType;
  target_item: string;
  criteria: string;
  is_active: boolean;
  created_at: string;
}

export interface CreateInspectionPlan {
  plan_code: string;
  plan_name: string;
  inspection_type?: InspectionType;
  target_item?: string;
  criteria?: string;
  is_active?: boolean;
}

export type UpdateInspectionPlan = Partial<CreateInspectionPlan>;

export interface InspectionResult {
  id: number;
  company: number | null;
  result_number: string;
  plan: number | null;
  item_name: string;
  lot_number: string;
  inspected_qty: number;
  passed_qty: number;
  failed_qty: number;
  result: InspectionResultValue;
  inspector: string;
  inspected_at: string | null;
  remark: string;
  created_at: string;
  /** Read-only computed property from the Django model. */
  pass_rate?: number;
}

export interface CreateInspectionResult {
  result_number: string;
  plan?: number | null;
  item_name: string;
  lot_number?: string;
  inspected_qty?: number;
  passed_qty?: number;
  failed_qty?: number;
  result?: InspectionResultValue;
  inspector?: string;
  inspected_at?: string | null;
  remark?: string;
}

export type UpdateInspectionResult = Partial<CreateInspectionResult>;

export interface DefectRecord {
  id: number;
  company: number | null;
  defect_number: string;
  inspection: number | null;
  item_name: string;
  defect_type: string;
  severity: DefectSeverity;
  quantity: number;
  description: string;
  detected_at: string | null;
  created_at: string;
}

export interface CreateDefectRecord {
  defect_number: string;
  inspection?: number | null;
  item_name: string;
  defect_type: string;
  severity?: DefectSeverity;
  quantity?: number;
  description?: string;
  detected_at?: string | null;
}

export type UpdateDefectRecord = Partial<CreateDefectRecord>;

export interface CorrectiveAction {
  id: number;
  company: number | null;
  capa_number: string;
  defect: number | null;
  title: string;
  root_cause: string;
  action_plan: string;
  responsible: string;
  due_date: string | null;
  status: CorrectiveActionStatus;
  completed_at: string | null;
  created_at: string;
}

export interface CreateCorrectiveAction {
  capa_number: string;
  defect?: number | null;
  title: string;
  root_cause?: string;
  action_plan?: string;
  responsible?: string;
  due_date?: string | null;
  status?: CorrectiveActionStatus;
}

export type UpdateCorrectiveAction = Partial<CreateCorrectiveAction>;

export interface SPCData {
  id: number;
  company: number;
  inspection_result: number;
  measurement_name: string;
  measured_value: string;
  usl: string | null;
  lsl: string | null;
  target: string | null;
  measured_at: string;
}

export type NcrStatus = "open" | "in_progress" | "closed" | "cancelled";

export interface NCR {
  id: number;
  company: number;
  ncr_number: string;
  defect_ref_number: string;
  title: string;
  description: string;
  root_cause: string;
  corrective_action: string;
  preventive_action: string;
  responsible: string;
  due_date: string | null;
  closed_date: string | null;
  status: NcrStatus;
  created_at: string;
}

export interface CreateNCR {
  ncr_number: string;
  defect_ref_number?: string;
  title: string;
  description: string;
  root_cause?: string;
  corrective_action?: string;
  preventive_action?: string;
  responsible?: string;
  due_date?: string | null;
  status?: NcrStatus;
}

export type UpdateNCR = Partial<CreateNCR>;
