import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const outputDir = "/Users/mac/Documents/ChatGPT/Bayer CMS/output";
const outputPath = `${outputDir}/Bayer_Veeva审批字段与截图枚举值.xlsx`;
const previewPath = `${outputDir}/Bayer_Veeva审批字段与截图枚举值_预览.png`;

const rows = [
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Please select", "占位提示", "截图1-2"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Content Module", "截图可见选项", "截图2"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Approval Not Needed Content", "截图可见选项", "截图2"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Claim", "截图可见选项", "截图2"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Component Asset", "截图可见选项", "截图2-3"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Corporate", "截图可见选项", "截图2-3"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Customer Consent", "截图可见选项", "截图2-3"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Email Fragment", "截图可见选项", "截图2-3"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Email Template", "截图可见选项", "截图2-3"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Event Material", "截图可见选项", "截图2-3"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Health Authority Form", "截图可见选项", "截图2-3"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "License Files", "截图可见选项", "截图2-3"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Market Access (Approval Needed)", "截图可见选项", "截图2-3"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Market Research (Approval Needed)", "截图可见选项", "截图2-3"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Material", "截图可见选项", "截图2-3"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Medical", "截图可见选项", "截图2-3"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Tracking Module", "截图可见选项", "截图2-3"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Module Map", "截图可见选项", "截图3"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Multichannel Slide", "截图可见选项", "截图3"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Reference", "截图可见选项", "截图3"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Type", "是", "Template Fragment", "截图可见选项", "截图3"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Subtype", "否", "截图未展示枚举值", "未展开", "截图1"],
  ["上传文件后需填写3个字段", "Upload Files (Step 1)", "Classification", "否", "截图未展示枚举值", "未展开", "截图1"],

  ["上传成功后填写General信息", "General 信息编辑", "Name", "是", "Mike-WSC Meet-the-Trialist Meeting 1022", "当前填写值", "截图4"],
  ["上传成功后填写General信息", "General 信息编辑", "Type", "未标识", "Medical", "当前显示值", "截图4-5"],
  ["上传成功后填写General信息", "General 信息编辑", "Therapeutic Area", "是", "Cardiovascular", "已选示例值", "截图5"],
  ["上传成功后填写General信息", "General 信息编辑", "Product", "是", "Depends on Thera...", "截断的依赖提示", "截图4"],
  ["上传成功后填写General信息", "General 信息编辑", "Product", "是", "Asundexian", "已选示例值", "截图5"],
  ["上传成功后填写General信息", "General 信息编辑", "Indication", "是", "Depends on Produ...", "截断的依赖提示", "截图4"],
  ["上传成功后填写General信息", "General 信息编辑", "Indication", "是", "FXIa Inhibitor", "已选示例值", "截图5"],
  ["上传成功后填写General信息", "General 信息编辑", "Country", "是", "RECENT", "选项分组标题", "截图5"],
  ["上传成功后填写General信息", "General 信息编辑", "Country", "是", "China", "截图可见选项", "截图5"],
  ["上传成功后填写General信息", "General 信息编辑", "Country", "是", "ALL", "选项分组标题", "截图5"],
  ["上传成功后填写General信息", "General 信息编辑", "Country", "是", "Afghanistan", "截图可见选项", "截图5"],
  ["上传成功后填写General信息", "General 信息编辑", "Country", "是", "Albania", "截图可见选项", "截图5"],
  ["上传成功后填写General信息", "General 信息编辑", "Country", "是", "Algeria", "截图可见选项", "截图5"],
  ["上传成功后填写General信息", "General 信息编辑", "Country", "是", "Angola", "截图可见选项", "截图5"],
  ["上传成功后填写General信息", "General 信息编辑", "Country", "是", "Antigua and Barbuda", "截图可见选项", "截图5"],
  ["上传成功后填写General信息", "General 信息编辑", "Country", "是", "Argentina", "截图可见选项", "截图5"],
  ["上传成功后填写General信息", "General 信息编辑", "Country", "是", "Armenia", "截图可见选项", "截图5"],
  ["上传成功后填写General信息", "General 信息编辑", "Mont Blanc ID (New US)", "未标识", "Depends on Lifecy...", "截断的依赖提示", "截图4"],
  ["上传成功后填写General信息", "General 信息编辑", "eWizard Preview", "未标识", "截图未展示枚举值", "未展开", "截图4-5"],
  ["上传成功后填写General信息", "General 信息编辑", "Audience", "是", "截图未展示枚举值", "未展开", "截图4-5"],
  ["上传成功后填写General信息", "General 信息编辑", "Branding", "是", "截图未展示枚举值", "未展开", "截图4-5"],
  ["上传成功后填写General信息", "General 信息编辑", "Campaign", "未标识", "截图未展示枚举值", "未展开", "截图4-5"],
  ["上传成功后填写General信息", "General 信息编辑", "Language", "是", "Chinese (Simplified)", "已选示例值", "截图6"],
  ["上传成功后填写General信息", "General 信息编辑", "CF Approval Number", "未标识", "截图未展示枚举值", "未展开", "截图5-6"],
  ["上传成功后填写General信息", "General 信息编辑", "Distribution Group", "未标识", "截图未展示枚举值", "未展开", "截图5-6"],
  ["上传成功后填写General信息", "General 信息编辑", "Medical Type", "是", "截图未展示枚举值", "未展开", "截图6"],
  ["上传成功后填写General信息", "General 信息编辑", "Distribution Mode", "是", "截图未展示枚举值", "未展开", "截图6"],
  ["上传成功后填写General信息", "General 信息编辑", "Condition of Use", "未标识", "截图未展示枚举值", "未展开", "截图6"],
  ["上传成功后填写General信息", "General 信息编辑", "Keywords", "未标识", "截图未展示枚举值", "未展开", "截图6"],
  ["上传成功后填写General信息", "General 信息编辑", "Rendition Profile", "未标识", "截图未展示枚举值", "未展开", "截图6"],
  ["上传成功后填写General信息", "General 信息编辑", "Version", "未标识", "0.1", "当前显示值", "截图6"],
  ["上传成功后填写General信息", "General 信息编辑", "Tags", "未标识", "截图未显示填写值", "空白/未显示", "截图6"],
  ["上传成功后填写General信息", "General 信息编辑", "Message Topic", "未标识", "截图未显示填写值", "空白/未显示", "截图6"],
  ["上传成功后填写General信息", "General 信息编辑", "AI usage for Images/videos/audio", "未标识", "截图未展示枚举值", "未展开", "截图6"],

  ["发起Review/Approval", "Start Review/Approval", "Material Owner (Responsible Bayer person who will receive expiration notifications)", "是", "Yan Liu", "已选示例值", "截图7"],
  ["发起Review/Approval", "Start Review/Approval", "Reviewers/Approvers 类型", "未标识", "Medical Reviewers/Approvers", "截图可见复选项", "截图7"],
  ["发起Review/Approval", "Start Review/Approval", "Reviewers/Approvers 类型", "未标识", "Regulatory Reviewers/Approvers", "截图可见复选项", "截图7"],
  ["发起Review/Approval", "Start Review/Approval", "Reviewers/Approvers 类型", "未标识", "Legal Reviewers/Approvers", "截图可见复选项", "截图7"],
  ["发起Review/Approval", "Start Review/Approval", "Reviewers/Approvers 类型", "未标识", "Other Reviewers/Approvers", "截图可见复选项", "截图7"],
  ["发起Review/Approval", "Start Review/Approval", "Review/Approval Due Date", "是", "dd MMM yyyy", "日期占位格式", "截图7"],
  ["发起Review/Approval", "Start Review/Approval", "CRM Product", "是", "Vericiguat [Verquvo] - CKD-CAD (CN)", "已选示例值", "截图7"],
  ["发起Review/Approval", "Start Review/Approval", "Distribution Group", "是", "截图未展示枚举值", "未展开", "截图7"],
  ["发起Review/Approval", "Start Review/Approval", "Duration Until Expiration", "是", "截图未展示枚举值", "未展开", "截图7"],

  ["右侧Information详情", "General 信息详情", "Name", "未标识", "Mike-WSC Meet-the-Trialist Meeting 1022", "当前显示值", "截图7"],
  ["右侧Information详情", "General 信息详情", "Description", "未标识", "截图未显示填写值", "空白/未显示", "截图7"],
  ["右侧Information详情", "General 信息详情", "Type", "未标识", "Medical", "当前显示值", "截图7"],
  ["右侧Information详情", "General 信息详情", "Therapeutic Area", "未标识", "Cardiovascular", "当前显示值", "截图7"],
  ["右侧Information详情", "General 信息详情", "Product", "未标识", "Vericiguat [Verquvo]", "当前显示值", "截图7"],
  ["右侧Information详情", "General 信息详情", "Indication", "未标识", "Chronic Heart Failure", "当前显示值", "截图7"],
  ["右侧Information详情", "General 信息详情", "Country", "未标识", "China", "当前显示值", "截图7"],
];

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const sheet = workbook.worksheets.getItem("字段与截图值");
for (const existingTable of sheet.tables.items) existingTable.delete();
sheet.getRange("A2:G2").unmerge();
sheet.getRange("A3:G3").unmerge();
sheet.getRange("A1:G200").clear({ applyTo: "all" });
sheet.freezePanes.unfreeze();
sheet.showGridLines = false;
sheet.tabColor = "#103B2D";

sheet.getRange("A2:G2").merge();
sheet.getRange("A2").values = [["Bayer Veeva 审批字段与截图可见值"]];
sheet.getRange("A2:G2").format = {
  font: { name: "Arial", size: 15, bold: true, color: "#183028" },
  verticalAlignment: "center",
};
sheet.getRange("A2:G2").format.rowHeight = 28;

sheet.getRange("A3:G3").merge();
sheet.getRange("A3").values = [["范围：依据补充版附件，仅整理截图中出现的字段和可见内容；未展开的下拉框不推测完整枚举值。"]];
sheet.getRange("A3:G3").format = {
  font: { name: "Arial", size: 10, italic: true, color: "#5B6470" },
  verticalAlignment: "center",
};
sheet.getRange("A4:G4").format.borders = { bottom: { style: "thin", color: "#AAB7B2" } };

const headers = [["大框架", "界面/步骤", "字段名称", "是否必填", "枚举值/截图显示值", "内容性质", "截图来源"]];
sheet.getRange("A6:G6").values = headers;
sheet.getRange(`A7:G${6 + rows.length}`).values = rows;

const full = sheet.getRange(`A6:G${6 + rows.length}`);
full.format = {
  font: { name: "Arial", size: 10, color: "#202624" },
  verticalAlignment: "center",
};
full.format.wrapText = true;

sheet.getRange("A6:G6").format = {
  fill: "#183028",
  font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: {
    insideVertical: { style: "thin", color: "#FFFFFF" },
    bottom: { style: "medium", color: "#183028" },
  },
};
sheet.getRange("A6:G6").format.rowHeight = 26;

for (let i = 0; i < rows.length; i++) {
  const excelRow = 7 + i;
  const group = rows[i][0];
  let fill = "#FFFFFF";
  if (group === "上传文件后需填写3个字段") fill = "#FFF4CC";
  if (group === "上传成功后填写General信息") fill = i % 2 === 0 ? "#F5F8F6" : "#FFFFFF";
  if (group === "发起Review/Approval") fill = i % 2 === 0 ? "#EAF2F8" : "#F7FBFD";
  if (group === "右侧Information详情") fill = i % 2 === 0 ? "#F3F0F7" : "#FAF8FC";
  sheet.getRange(`A${excelRow}:G${excelRow}`).format.fill = fill;
  sheet.getRange(`A${excelRow}:G${excelRow}`).format.borders = {
    bottom: { style: "thin", color: "#D7DEDB" },
  };
}

sheet.getRange(`D7:D${6 + rows.length}`).format.horizontalAlignment = "center";
sheet.getRange(`G7:G${6 + rows.length}`).format.horizontalAlignment = "center";
sheet.getRange(`F7:F${6 + rows.length}`).format.font = { name: "Arial", size: 10, color: "#475569", italic: true };

sheet.getRange("A:A").format.columnWidth = 25;
sheet.getRange("B:B").format.columnWidth = 24;
sheet.getRange("C:C").format.columnWidth = 42;
sheet.getRange("D:D").format.columnWidth = 12;
sheet.getRange("E:E").format.columnWidth = 36;
sheet.getRange("F:F").format.columnWidth = 18;
sheet.getRange("G:G").format.columnWidth = 12;
sheet.getRange(`A7:G${6 + rows.length}`).format.autofitRows();
sheet.freezePanes.freezeRows(6);

const table = sheet.tables.add(`A6:G${6 + rows.length}`, true, "VeevaFieldsTable");
table.style = "TableStyleMedium2";
table.showBandedRows = false;
table.showFilterButton = true;

workbook.recalculate();
const check = await workbook.inspect({
  kind: "table",
  range: `字段与截图值!A1:G${6 + rows.length}`,
  include: "values,formulas",
  tableMaxRows: 100,
  tableMaxCols: 8,
});
console.log(check.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

const preview = await workbook.render({
  sheetName: "字段与截图值",
  range: `A1:G${6 + rows.length}`,
  scale: 1.4,
  format: "png",
});
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));

console.log(JSON.stringify({ outputPath, previewPath, rowCount: rows.length }));
