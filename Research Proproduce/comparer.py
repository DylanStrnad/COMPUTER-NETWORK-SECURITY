import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import time


def parse_truth_file(path: str) -> dict:
    flows = {}
    with Path(path).open("r", encoding="utf-8") as source:
        for line_number, raw_line in enumerate(source, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = {}
            for piece in line.split(","):
                chunk = piece.strip()
                if not chunk:
                    continue
                if ":" not in chunk:
                    raise ValueError(
                        f"Malformed truth flow at line {line_number}: {line}"
                    )
                key, value = chunk.split(":", 1)
                parts[key.strip().lower()] = value.strip()

            for key in ("flow_id", "match", "action"):
                if key not in parts:
                    raise ValueError(
                        f"Malformed truth flow at line {line_number}: missing {key}"
                    )

            flow_id = parts["flow_id"]
            flows[flow_id] = {"match": parts["match"], "action": parts["action"]}

    return flows


def parse_report_file(path: str) -> dict:
    with Path(path).open("r", encoding="utf-8") as source:
        data = json.load(source)

    if not isinstance(data, dict) or not isinstance(data.get("flows"), list):
        raise ValueError("report JSON must contain a top-level 'flows' list")

    flows = {}
    for index, item in enumerate(data["flows"]):
        if not isinstance(item, dict):
            raise ValueError(f"Malformed report flow at index {index}")

        for key in ("id", "match", "action"):
            if key not in item:
                raise ValueError(
                    f"Malformed report flow at index {index}: missing {key}"
                )

        flow_id = str(item["id"]).strip()
        flows[flow_id] = {
            "match": str(item["match"]).strip(),
            "action": str(item["action"]).strip(),
        }

    return flows

def print_execution_time(start, end):
    total_time = (end - start) * 1000
    print(f"{total_time:.2f}ms")

def run_audit(truth_path: str, report_path: str):
    truth_flows = parse_truth_file(truth_path)
    report_flows = parse_report_file(report_path)

    truth_ids = set(truth_flows.keys())
    report_ids = set(report_flows.keys())

    hidden_ids = sorted(truth_ids - report_ids)
    extra_ids = sorted(report_ids - truth_ids)
    verified_ids = []
    tampered_ids = []

    for flow_id in sorted(truth_ids & report_ids):
        expected = truth_flows[flow_id]
        observed = report_flows[flow_id]
        if expected["match"] == observed["match"] and expected["action"] == observed["action"]:
            verified_ids.append(flow_id)
        else:
            tampered_ids.append(flow_id)

    summary = {
        "truth_count": len(truth_flows),
        "report_count": len(report_flows),
        "verified_ids": verified_ids,
        "hidden_ids": hidden_ids,
        "extra_ids": extra_ids,
        "tampered_ids": tampered_ids,
        "incident_found": bool(hidden_ids or extra_ids or tampered_ids),
    }
    return summary, truth_flows, report_flows


def build_report_text(summary: dict, truth_flows: dict, report_flows: dict, start_time, end_time) -> str:
    lines = [
        "=== SDN Flow Audit ===",
        f"Switch truth flows:      {summary['truth_count']}",
        f"Controller report flows: {summary['report_count']}",
        f"Verified flows:          {len(summary['verified_ids'])}",
        f"Hidden flows:            {len(summary['hidden_ids'])}",
        f"Extra flows:             {len(summary['extra_ids'])}",
        f"Tampered flows:          {len(summary['tampered_ids'])}",
    ]

    if summary["hidden_ids"]:
        lines.append("\nHidden flows:")
        for flow_id in summary["hidden_ids"]:
            flow = truth_flows[flow_id]
            lines.append(
                f"  - id={flow_id}, match={flow['match']}, action={flow['action']}"
            )

    if summary["extra_ids"]:
        lines.append("\nExtra flows:")
        for flow_id in summary["extra_ids"]:
            flow = report_flows[flow_id]
            lines.append(
                f"  - id={flow_id}, match={flow['match']}, action={flow['action']}"
            )

    if summary["tampered_ids"]:
        lines.append("\nTampered flows:")
        for flow_id in summary["tampered_ids"]:
            expected = truth_flows[flow_id]
            observed = report_flows[flow_id]
            lines.append(f"  - id={flow_id}")
            lines.append(
                f"    expected: match={expected['match']}, action={expected['action']}"
            )
            lines.append(
                f"    observed: match={observed['match']}, action={observed['action']}"
            )

    if summary["incident_found"]:
        lines.append("\nSECURITY INCIDENT FOUND")
    else:
        lines.append("\nAudit complete. No incident detected.")

    total = (end_time - start_time) * 1000
    lines.append (f"Total run time: {total:.2f}ms")

    return "\n".join(lines)


class AuditApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("SDN Flow Audit")
        self.root.geometry("920x620")

        self.truth_var = tk.StringVar(value="network.txt")
        self.report_var = tk.StringVar(value="report.json")

        self._build_ui()

    def _build_ui(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Header.TLabel", font=("Segoe UI Semibold", 16))

        container = ttk.Frame(self.root, padding=14)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="SDN Flow Audit Dashboard", style="Header.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        ttk.Label(container, text="Truth file:").grid(row=1, column=0, sticky="w")
        ttk.Entry(container, textvariable=self.truth_var).grid(
            row=1, column=1, sticky="ew", padx=8
        )
        ttk.Button(container, text="Browse", command=self._browse_truth).grid(
            row=1, column=2
        )

        ttk.Label(container, text="Report file:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(container, textvariable=self.report_var).grid(
            row=2, column=1, sticky="ew", padx=8, pady=(8, 0)
        )
        ttk.Button(container, text="Browse", command=self._browse_report).grid(
            row=2, column=2, pady=(8, 0)
        )

        ttk.Button(container, text="Run Audit", command=self._run).grid(
            row=3, column=0, sticky="w", pady=12
        )

        self.status_label = ttk.Label(container, text="Ready", foreground="#1f6d1f")
        self.status_label.grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 8))

        self.output_box = ScrolledText(
            container, wrap="word", font=("Consolas", 10), bg="#f8fafc", height=24
        )
        self.output_box.grid(row=5, column=0, columnspan=3, sticky="nsew")

        container.columnconfigure(1, weight=1)
        container.rowconfigure(5, weight=1)

    def _browse_truth(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select truth file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if selected:
            self.truth_var.set(selected)

    def _browse_report(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select report file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if selected:
            self.report_var.set(selected)

    def _run(self) -> None:
        truth_path = self.truth_var.get().strip()
        report_path = self.report_var.get().strip()

        if not truth_path or not report_path:
            messagebox.showwarning("Missing input", "Please provide both input files.")
            return

        try:
            start_time = time.time()
            summary, truth_flows, report_flows = run_audit(truth_path, report_path)
            end_time = time.time()
        except FileNotFoundError as exc:
            messagebox.showerror("File error", f"Input file not found:\n{exc}")
            return
        except json.JSONDecodeError as exc:
            messagebox.showerror("JSON error", f"Invalid JSON in report file:\n{exc}")
            return
        except ValueError as exc:
            messagebox.showerror("Data error", str(exc))
            return
        
        report_text = build_report_text(summary, truth_flows, report_flows, start_time, end_time)
        self.output_box.delete("1.0", tk.END)
        self.output_box.insert(tk.END, report_text)

        if summary["incident_found"]:
            self.status_label.configure(
                text="Incident detected. Review findings below.", foreground="#9b1c1c"
            )
        else:
            self.status_label.configure(
                text="No incident detected.", foreground="#1f6d1f"
            )


def main() -> None:
    root = tk.Tk()
    AuditApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
