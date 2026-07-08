import customtkinter as ctk
from tkinter import filedialog
import threading

from services.knowledge_ingestion_service import KnowledgeIngestionService
from services.knowledge_service import KnowledgeService
from services.logging_service import LoggingService


logger = LoggingService.get_logger("content")


class KnowledgePage(ctk.CTkFrame):

    TABLE_LABELS = {
        "programs": "Programs",
        "apparatus": "Apparatus",
        "annual_events": "Annual Events",
        "locations": "Locations",
        "response_area": "Response Area",
        "community_partners": "Community Partners"
    }

    def __init__(self, parent):

        super().__init__(parent)

        self.service = KnowledgeService()
        self.ingestion_service = KnowledgeIngestionService(
            knowledge_service=self.service
        )
        self.current_table = "programs"
        self.current_item_id = None
        self.pending_import = None

        self.build_page()
        self.load_profile()
        self.load_items()
        self.refresh_statistics()

    ##########################################################

    def build_page(self):

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        heading = ctk.CTkLabel(
            self,
            text="Department Knowledge",
            font=("Segoe UI", 30, "bold")
        )

        heading.grid(
            row=0,
            column=0,
            sticky="w",
            padx=20,
            pady=(20, 8)
        )

        self.profile_frame = ctk.CTkFrame(self)

        self.profile_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 12)
        )
        self.profile_frame.grid_columnconfigure(1, weight=1)
        self.profile_frame.grid_columnconfigure(3, weight=1)

        self.profile_entries = {}
        fields = (
            ("department_name", "Department"),
            ("short_name", "Short Name"),
            ("community", "Community"),
            ("province", "Province"),
            ("voice", "Voice")
        )

        for index, (key, label) in enumerate(fields):
            row = index // 2
            column = (index % 2) * 2

            ctk.CTkLabel(
                self.profile_frame,
                text=label
            ).grid(
                row=row,
                column=column,
                sticky="w",
                padx=12,
                pady=6
            )

            entry = ctk.CTkEntry(self.profile_frame)
            entry.grid(
                row=row,
                column=column + 1,
                sticky="ew",
                padx=(0, 12),
                pady=6
            )
            self.profile_entries[key] = entry

        save_profile = ctk.CTkButton(
            self.profile_frame,
            text="Save Profile",
            command=self.save_profile
        )

        save_profile.grid(
            row=3,
            column=0,
            sticky="w",
            padx=12,
            pady=(6, 12)
        )

        import_controls = ctk.CTkFrame(
            self.profile_frame,
            fg_color="transparent"
        )

        import_controls.grid(
            row=3,
            column=1,
            columnspan=3,
            sticky="ew",
            padx=(0, 12),
            pady=(6, 12)
        )

        import_button = ctk.CTkButton(
            import_controls,
            text="Import Documents",
            command=self.import_documents
        )

        import_button.pack(
            side="left",
            padx=(0, 8)
        )

        review_button = ctk.CTkButton(
            import_controls,
            text="Review Import",
            command=self.review_import
        )

        review_button.pack(
            side="left",
            padx=(0, 8)
        )

        apply_button = ctk.CTkButton(
            import_controls,
            text="Apply Changes",
            command=self.apply_import
        )

        apply_button.pack(
            side="left",
            padx=(0, 8)
        )

        discard_button = ctk.CTkButton(
            import_controls,
            text="Discard Changes",
            command=self.discard_import
        )

        discard_button.pack(
            side="left"
        )

        self.stats_label = ctk.CTkLabel(
            self.profile_frame,
            text="Knowledge Statistics",
            justify="left"
        )

        self.stats_label.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="w",
            padx=12,
            pady=(0, 12)
        )

        self.import_summary_label = ctk.CTkLabel(
            self.profile_frame,
            text="Import Summary: no pending import",
            justify="left"
        )

        self.import_summary_label.grid(
            row=4,
            column=2,
            columnspan=2,
            sticky="w",
            padx=12,
            pady=(0, 12)
        )

        body = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        body.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=20,
            pady=(0, 20)
        )
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(1, weight=1)

        self.table_menu = ctk.CTkOptionMenu(
            body,
            values=list(self.TABLE_LABELS.values()),
            command=self.change_table
        )

        self.table_menu.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 12),
            pady=(0, 10)
        )

        new_button = ctk.CTkButton(
            body,
            text="New Item",
            command=self.new_item
        )

        new_button.grid(
            row=0,
            column=1,
            sticky="w",
            pady=(0, 10)
        )

        self.item_list = ctk.CTkScrollableFrame(
            body,
            width=300
        )

        self.item_list.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(0, 12)
        )

        form = ctk.CTkFrame(body)

        form.grid(
            row=1,
            column=1,
            sticky="nsew"
        )
        form.grid_columnconfigure(1, weight=1)

        self.name_entry = self.add_entry(form, 0, "Name")
        self.category_entry = self.add_entry(form, 1, "Category")
        self.tags_entry = self.add_entry(form, 2, "Tags")

        ctk.CTkLabel(
            form,
            text="Description"
        ).grid(
            row=3,
            column=0,
            sticky="nw",
            padx=12,
            pady=8
        )

        self.description_text = ctk.CTkTextbox(
            form,
            height=120
        )

        self.description_text.grid(
            row=3,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=8
        )

        self.active_var = ctk.BooleanVar(value=True)
        active = ctk.CTkCheckBox(
            form,
            text="Active",
            variable=self.active_var
        )

        active.grid(
            row=4,
            column=1,
            sticky="w",
            padx=(0, 12),
            pady=8
        )

        controls = ctk.CTkFrame(
            form,
            fg_color="transparent"
        )

        controls.grid(
            row=5,
            column=1,
            sticky="w",
            padx=(0, 12),
            pady=(8, 12)
        )

        save = ctk.CTkButton(
            controls,
            text="Save Item",
            command=self.save_item
        )

        save.pack(
            side="left",
            padx=(0, 8)
        )

        delete = ctk.CTkButton(
            controls,
            text="Delete Item",
            command=self.delete_item
        )

        delete.pack(
            side="left"
        )

        self.status = ctk.CTkLabel(
            form,
            text=""
        )

        self.status.grid(
            row=6,
            column=1,
            sticky="w",
            padx=(0, 12),
            pady=(0, 12)
        )

    ##########################################################

    def add_entry(self, parent, row, label):

        ctk.CTkLabel(
            parent,
            text=label
        ).grid(
            row=row,
            column=0,
            sticky="w",
            padx=12,
            pady=8
        )

        entry = ctk.CTkEntry(parent)

        entry.grid(
            row=row,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=8
        )

        return entry

    ##########################################################

    def load_profile(self):

        profile = self.service.profile()

        for key, entry in self.profile_entries.items():
            entry.delete(0, "end")
            entry.insert(
                0,
                profile.get(
                    key,
                    ""
                )
            )

    ##########################################################

    def save_profile(self):

        self.service.save_profile(
            {
                key: entry.get().strip()
                for key, entry in self.profile_entries.items()
            }
        )
        self.status.configure(
            text="Profile saved."
        )
        self.refresh_statistics()

    ##########################################################

    def import_documents(self):

        paths = filedialog.askopenfilenames(
            title="Import Knowledge Documents",
            filetypes=[
                (
                    "Knowledge Documents",
                    "*.pdf *.docx *.txt *.md *.markdown *.rtf *.csv"
                ),
                ("All Files", "*.*")
            ]
        )

        if not paths:
            return

        self.status.configure(
            text="Importing documents..."
        )

        def worker():

            try:
                result = self.ingestion_service.import_documents(paths)
                self.after(
                    0,
                    lambda: self.import_complete(result)
                )

            except Exception as ex:
                message = str(ex)
                logger.error(
                    "Knowledge import failed",
                    exc_info=(
                        type(ex),
                        ex,
                        ex.__traceback__
                    )
                )
                self.after(
                    0,
                    lambda: self.status.configure(
                        text=f"Import failed: {message}"
                    )
                )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    ##########################################################

    def import_complete(self, result):

        self.pending_import = result
        self.render_import_summary()
        self.review_import()
        self.status.configure(
            text="Import ready for review."
        )

    ##########################################################

    def review_import(self):

        if not self.pending_import:
            self.status.configure(
                text="No pending import to review."
            )
            return

        for child in self.item_list.winfo_children():
            child.destroy()

        for record in self.pending_import.get("records", []):
            text = (
                f"{record['status'].upper()} | "
                f"{self.TABLE_LABELS.get(record['table'], record['table'])} | "
                f"{self.record_name(record)}"
            )
            button = ctk.CTkButton(
                self.item_list,
                text=text,
                command=lambda value=record: self.load_import_record(value)
            )

            button.pack(
                fill="x",
                padx=8,
                pady=4
            )

        self.status.configure(
            text="Reviewing pending import."
        )

    ##########################################################

    def load_import_record(self, record):

        item = record["item"]
        self.current_item_id = None

        if record["table"] == "department_profile":
            self.name_entry.delete(0, "end")
            self.name_entry.insert(
                0,
                item.get("key", "")
            )
            self.category_entry.delete(0, "end")
            self.category_entry.insert(0, "department_profile")
            self.tags_entry.delete(0, "end")
            self.description_text.delete("1.0", "end")
            self.description_text.insert(
                "1.0",
                item.get("value", "")
            )
        else:
            self.name_entry.delete(0, "end")
            self.name_entry.insert(
                0,
                item.get("name", "")
            )
            self.category_entry.delete(0, "end")
            self.category_entry.insert(
                0,
                item.get("category", "")
            )
            self.tags_entry.delete(0, "end")
            self.tags_entry.insert(
                0,
                ", ".join(item.get("tags", []))
            )
            self.description_text.delete("1.0", "end")
            self.description_text.insert(
                "1.0",
                item.get("description", "")
            )

        self.active_var.set(True)
        self.status.configure(
            text=(
                f"{record['status'].title()} import record from "
                f"{record.get('source', '')}"
            )
        )

    ##########################################################

    def apply_import(self):

        if not self.pending_import:
            self.status.configure(
                text="No pending import to apply."
            )
            return

        result = self.service.apply_import(
            self.pending_import
        )
        self.pending_import = None
        self.load_profile()
        self.load_items()
        self.refresh_statistics()
        self.render_import_summary(
            {
                "imported": result["applied"],
                "skipped": result["skipped"],
                "duplicates": 0,
                "conflicts": 0,
                "new_programs": 0,
                "new_apparatus": 0,
                "new_events": 0,
                "new_partners": 0,
                "new_locations": 0
            }
        )
        self.status.configure(
            text=f"Applied {result['applied']} import changes."
        )

    ##########################################################

    def discard_import(self):

        self.pending_import = None
        self.load_items()
        self.render_import_summary()
        self.status.configure(
            text="Pending import discarded."
        )

    ##########################################################

    def refresh_statistics(self):

        stats = self.service.statistics()
        self.stats_label.configure(
            text=(
                "Knowledge Statistics\n"
                f"Programs: {stats['programs']} | "
                f"Apparatus: {stats['apparatus']} | "
                f"Events: {stats['events']}\n"
                f"Partners: {stats['partners']} | "
                f"Locations: {stats['locations']} | "
                f"Documents Imported: {stats['documents_imported']}\n"
                f"Completeness: {stats['knowledge_completeness_score']}%"
            )
        )

    ##########################################################

    def render_import_summary(self, summary=None):

        if summary is None and self.pending_import:
            summary = self.pending_import.get(
                "summary",
                {}
            )

        if not summary:
            self.import_summary_label.configure(
                text="Import Summary: no pending import"
            )
            return

        self.import_summary_label.configure(
            text=(
                "Import Summary\n"
                f"Imported: {summary.get('imported', 0)} | "
                f"Skipped: {summary.get('skipped', 0)} | "
                f"Duplicates: {summary.get('duplicates', 0)} | "
                f"Conflicts: {summary.get('conflicts', 0)}\n"
                f"New Programs: {summary.get('new_programs', 0)} | "
                f"New Apparatus: {summary.get('new_apparatus', 0)} | "
                f"New Events: {summary.get('new_events', 0)} | "
                f"New Partners: {summary.get('new_partners', 0)} | "
                f"New Locations: {summary.get('new_locations', 0)}"
            )
        )

    ##########################################################

    def record_name(self, record):

        item = record.get(
            "item",
            {}
        )

        return item.get("name") or item.get("key") or ""

    ##########################################################

    def change_table(self, label):

        for key, value in self.TABLE_LABELS.items():

            if value == label:
                self.current_table = key
                break

        self.new_item()
        self.load_items()

    ##########################################################

    def load_items(self):

        for child in self.item_list.winfo_children():
            child.destroy()

        for item in self.service.items(self.current_table):
            button = ctk.CTkButton(
                self.item_list,
                text=item["name"],
                command=lambda value=item: self.load_item(value)
            )

            button.pack(
                fill="x",
                padx=8,
                pady=4
            )

    ##########################################################

    def load_item(self, item):

        self.current_item_id = item.get("id")
        self.name_entry.delete(0, "end")
        self.name_entry.insert(
            0,
            item.get("name", "")
        )
        self.category_entry.delete(0, "end")
        self.category_entry.insert(
            0,
            item.get("category", "")
        )
        self.tags_entry.delete(0, "end")
        self.tags_entry.insert(
            0,
            ", ".join(item.get("tags", []))
        )
        self.description_text.delete("1.0", "end")
        self.description_text.insert(
            "1.0",
            item.get("description", "")
        )
        self.active_var.set(
            item.get("active", True)
        )
        self.status.configure(
            text=f"Editing {item.get('name', '')}"
        )

    ##########################################################

    def new_item(self):

        self.current_item_id = None
        self.name_entry.delete(0, "end")
        self.category_entry.delete(0, "end")
        self.tags_entry.delete(0, "end")
        self.description_text.delete("1.0", "end")
        self.active_var.set(True)
        self.status.configure(
            text="New item"
        )

    ##########################################################

    def save_item(self):

        name = self.name_entry.get().strip()

        if not name:
            self.status.configure(
                text="Name is required."
            )
            return

        item = {
            "id": self.current_item_id,
            "name": name,
            "category": self.category_entry.get().strip(),
            "description": self.description_text.get("1.0", "end").strip(),
            "tags": [
                tag.strip()
                for tag in self.tags_entry.get().split(",")
                if tag.strip()
            ],
            "active": self.active_var.get()
        }
        self.current_item_id = self.service.save_item(
            self.current_table,
            item
        )
        self.load_items()
        self.refresh_statistics()
        self.status.configure(
            text="Item saved."
        )

        logger.info(
            "Knowledge item saved table=%s id=%s",
            self.current_table,
            self.current_item_id
        )

    ##########################################################

    def delete_item(self):

        if not self.current_item_id:
            self.status.configure(
                text="Select an item to delete."
            )
            return

        self.service.delete_item(
            self.current_table,
            self.current_item_id
        )
        deleted_id = self.current_item_id
        self.new_item()
        self.load_items()
        self.refresh_statistics()
        self.status.configure(
            text="Item deleted."
        )

        logger.info(
            "Knowledge item deleted table=%s id=%s",
            self.current_table,
            deleted_id
        )
