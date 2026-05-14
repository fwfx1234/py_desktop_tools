from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot, Property


class QmlDemoViewModel(QObject):
    """ViewModel for interactive QML demos: counters, form data, ListView models."""

    countChanged = Signal()
    colorChanged = Signal()
    formDataChanged = Signal()
    listDataChanged = Signal()
    messageReceived = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._count: int = 0
        self._color: str = "#8B5CF6"
        self._name: str = ""
        self._email: str = ""
        self._selected_tab: int = 0
        self._items: list[dict] = [
            {"name": "Apple", "category": "水果", "price": "¥5.00"},
            {"name": "Banana", "category": "水果", "price": "¥3.50"},
            {"name": "Orange", "category": "水果", "price": "¥4.00"},
            {"name": "Broccoli", "category": "蔬菜", "price": "¥6.50"},
            {"name": "Carrot", "category": "蔬菜", "price": "¥2.80"},
            {"name": "Milk", "category": "乳制品", "price": "¥8.00"},
            {"name": "Cheese", "category": "乳制品", "price": "¥15.00"},
            {"name": "Egg", "category": "蛋白质", "price": "¥1.20"},
        ]
        self._filtered_items: list[dict] = list(self._items)

    # ---- count ----
    def _get_count(self) -> int: return self._count
    def _set_count(self, v: int):
        if self._count != v: self._count = v; self.countChanged.emit()
    count = Property(int, _get_count, _set_count, notify=countChanged)

    # ---- color ----
    def _get_color(self) -> str: return self._color
    def _set_color(self, v: str):
        if self._color != v: self._color = v; self.colorChanged.emit()
    demoColor = Property(str, _get_color, _set_color, notify=colorChanged)

    # ---- form fields ----
    def _get_name(self) -> str: return self._name
    def _set_name(self, v: str):
        if self._name != v: self._name = v; self.formDataChanged.emit()
    formName = Property(str, _get_name, _set_name, notify=formDataChanged)

    def _get_email(self) -> str: return self._email
    def _set_email(self, v: str):
        if self._email != v: self._email = v; self.formDataChanged.emit()
    formEmail = Property(str, _get_email, _set_email, notify=formDataChanged)

    # ---- list items ----
    def _get_items(self) -> list[dict]: return self._filtered_items
    items = Property("QVariantList", _get_items, constant=True)

    # ---- Slots ----
    @Slot()
    def increment(self) -> None:
        self._count += 1
        self.countChanged.emit()

    @Slot()
    def decrement(self) -> None:
        self._count -= 1
        self.countChanged.emit()

    @Slot()
    def resetCount(self) -> None:
        self._count = 0
        self.countChanged.emit()

    @Slot(str)
    def setDemoColor(self, color: str) -> None:
        self._color = color
        self.colorChanged.emit()

    @Slot(str)
    def filterItems(self, query: str) -> None:
        q = (query or "").lower()
        if not q:
            self._filtered_items = list(self._items)
        else:
            self._filtered_items = [
                it for it in self._items
                if q in it["name"].lower() or q in it["category"]
            ]
        self.listDataChanged.emit()

    @Slot(str)
    def sendMessage(self, text: str) -> None:
        self.messageReceived.emit(f"收到消息: {text}")

    @Slot()
    def submitForm(self) -> None:
        msg = f"提交成功！姓名: {self._name}, 邮箱: {self._email}"
        self.messageReceived.emit(msg)

    @Slot(result=str)
    def getGreeting(self) -> str:
        hour = __import__("datetime").datetime.now().hour
        if hour < 12: return "早上好！"
        elif hour < 18: return "下午好！"
        else: return "晚上好！"

    def dispose(self) -> None:
        for sig in [self.countChanged, self.colorChanged, self.formDataChanged,
                     self.listDataChanged, self.messageReceived]:
            try: sig.disconnect()
            except RuntimeError: pass
