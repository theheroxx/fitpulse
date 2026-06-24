# ui/desktop/widgets/records_page.py
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from datetime import datetime
import json
import os

# Import from your database
from database.exercise import get_exercises
from database.db import save_record, get_user_records, update_record, delete_record
from database.food import get_all_foods, get_food_by_id


class FoodItemWidget(QWidget):
    """Compact widget for displaying a food item in a meal"""
    
    remove_food = Signal(object)
    food_updated = Signal()
    
    def __init__(self, food_data, serving_size=1.0):
        super().__init__()
        self.food_data = food_data
        self.serving_size = serving_size
        self.setup_ui()
    
    def setup_ui(self):
        self.setObjectName("food_item")
        self.setFixedHeight(50)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)
        
        # Food icon
        icon_label = QLabel(self.get_food_icon())
        icon_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(icon_label)
        
        # Food info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)
        
        name_label = QLabel(self.food_data['name'])
        name_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        name_label.setStyleSheet("color: #1e293b;")
        info_layout.addWidget(name_label)
        
        # Get nutrition values (using correct column names from your DB)
        calories_per_100g = self.food_data.get('calories_per_100g', 0)
        protein_per_100g = self.food_data.get('protein_g', 0)
        carbs_per_100g = self.food_data.get('carbs_g', 0)
        fats_per_100g = self.food_data.get('fat_g', 0)
        
        # Calculate based on serving size (1 serving = 100g)
        calories = calories_per_100g * self.serving_size
        protein = protein_per_100g * self.serving_size
        carbs = carbs_per_100g * self.serving_size
        fats = fats_per_100g * self.serving_size
        
        nutrition_text = f"{calories:.0f} kcal • {protein:.1f}g protein • {carbs:.1f}g carbs • {fats:.1f}g fat"
        self.nutrition_label = QLabel(nutrition_text)
        self.nutrition_label.setStyleSheet("color: #64748b; font-size: 10px;")
        info_layout.addWidget(self.nutrition_label)
        
        layout.addLayout(info_layout, 1)
        
        # Serving size
        serving_layout = QHBoxLayout()
        serving_layout.setSpacing(5)
        
        serving_label = QLabel("Serving:")
        serving_label.setStyleSheet("color: #64748b; font-size: 10px;")
        serving_layout.addWidget(serving_label)
        
        self.serving_spinbox = QDoubleSpinBox()
        self.serving_spinbox.setRange(0.25, 10)
        self.serving_spinbox.setValue(self.serving_size)
        self.serving_spinbox.setSuffix(" serving (100g)")
        self.serving_spinbox.setSingleStep(0.25)
        self.serving_spinbox.setFixedWidth(130)
        self.serving_spinbox.setStyleSheet("""
            QDoubleSpinBox {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 3px 6px;
                font-size: 10px;
                background: white;
            }
            QDoubleSpinBox:hover {
                border-color: #cbd5e1;
            }
        """)
        self.serving_spinbox.valueChanged.connect(self.update_nutrition)
        serving_layout.addWidget(self.serving_spinbox)
        
        layout.addLayout(serving_layout)
        
        # Remove button
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #ef4444;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #fee2e2;
                border-radius: 12px;
            }
        """)
        remove_btn.clicked.connect(lambda: self.remove_food.emit(self))
        layout.addWidget(remove_btn)
        
        # Card styling
        self.setStyleSheet("""
            #food_item {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
            #food_item:hover {
                border-color: #cbd5e1;
            }
        """)
    
    def get_food_icon(self):
        """Return appropriate icon based on food type"""
        name = self.food_data['name'].lower()
        category = self.food_data.get('category', '').lower()
        
        if 'chicken' in name or 'meat' in name or category == 'meat':
            return "🍗"
        elif 'fish' in name or 'salmon' in name or category == 'fish':
            return "🐟"
        elif 'rice' in name or 'pasta' in name or 'bread' in name or category == 'grains':
            return "🍚"
        elif 'apple' in name or 'banana' in name or 'fruit' in name or category == 'fruit':
            return "🍎"
        elif 'broccoli' in name or 'vegetable' in name or 'salad' in name or category == 'vegetable':
            return "🥦"
        elif 'egg' in name:
            return "🥚"
        elif 'milk' in name or 'cheese' in name or 'yogurt' in name or category == 'dairy':
            return "🥛"
        else:
            return "🍽️"
    
    def update_nutrition(self, value):
        """Update nutrition display when serving size changes"""
        self.serving_size = value
        
        calories_per_100g = self.food_data.get('calories_per_100g', 0)
        protein_per_100g = self.food_data.get('protein_g', 0)
        carbs_per_100g = self.food_data.get('carbs_g', 0)
        fats_per_100g = self.food_data.get('fat_g', 0)
        
        calories = calories_per_100g * value
        protein = protein_per_100g * value
        carbs = carbs_per_100g * value
        fats = fats_per_100g * value
        
        self.nutrition_label.setText(f"{calories:.0f} kcal • {protein:.1f}g protein • {carbs:.1f}g carbs • {fats:.1f}g fat")
        
        # Emit signal that food was updated
        self.food_updated.emit()
    
    def get_food_with_serving(self):
        """Return food data with serving size"""
        food_copy = self.food_data.copy()
        food_copy['serving_size'] = self.serving_size
        food_copy['calories'] = self.food_data.get('calories_per_100g', 0) * self.serving_size
        return food_copy


class MealWidget(QWidget):
    """Widget for a single meal containing multiple foods"""
    
    meal_updated = Signal()
    
    def __init__(self, meal_name="Meal 1", foods=None):
        super().__init__()
        self.meal_name = meal_name
        self.foods = foods or []
        self.all_foods = []
        self.setup_ui()
        self.load_foods_from_db()
    
    def setup_ui(self):
        self.setObjectName("meal_widget")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Meal card
        card = QWidget()
        card.setObjectName("meal_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)
        
        # Meal header
        header_layout = QHBoxLayout()
        
        # Meal icon and name
        meal_header_left = QHBoxLayout()
        meal_icon = QLabel("🍽️")
        meal_icon.setStyleSheet("font-size: 18px;")
        meal_header_left.addWidget(meal_icon)
        
        self.meal_label = QLabel(self.meal_name)
        self.meal_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.meal_label.setStyleSheet("color: #1e293b;")
        meal_header_left.addWidget(self.meal_label)
        
        # Meal total calories
        self.total_calories_label = QLabel("0 kcal")
        self.total_calories_label.setStyleSheet("color: #8b5cf6; font-size: 12px; font-weight: 600; margin-left: 10px;")
        meal_header_left.addWidget(self.total_calories_label)
        
        header_layout.addLayout(meal_header_left)
        header_layout.addStretch()
        
        # Remove meal button
        self.remove_meal_btn = QPushButton("×")
        self.remove_meal_btn.setFixedSize(28, 28)
        self.remove_meal_btn.setCursor(Qt.PointingHandCursor)
        self.remove_meal_btn.setToolTip("Remove meal")
        self.remove_meal_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
                color: #ef4444;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #fee2e2;
                border-color: #fecaca;
            }
        """)
        header_layout.addWidget(self.remove_meal_btn)
        
        card_layout.addLayout(header_layout)
        
        # Foods container
        self.foods_container = QWidget()
        self.foods_layout = QVBoxLayout(self.foods_container)
        self.foods_layout.setContentsMargins(0, 0, 0, 0)
        self.foods_layout.setSpacing(6)
        
        # Empty state
        self.empty_label = QLabel("No foods added yet. Search and add foods below.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #94a3b8; font-size: 11px; padding: 12px;")
        self.foods_layout.addWidget(self.empty_label)
        
        card_layout.addWidget(self.foods_container)
        
        # Separator
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background: #e2e8f0;")
        card_layout.addWidget(separator)
        
        # Add food section
        add_food_layout = QHBoxLayout()
        add_food_layout.setSpacing(8)
        
        # Search icon
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("font-size: 14px;")
        add_food_layout.addWidget(search_icon)
        
        self.food_combo = QComboBox()
        self.food_combo.setEditable(True)
        self.food_combo.setPlaceholderText("Search food...")
        self.food_combo.setMinimumWidth(200)
        self.food_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
                background: white;
            }
            QComboBox:hover {
                border-color: #cbd5e1;
            }
            QComboBox:focus {
                border-color: #8b5cf6;
            }
        """)
        add_food_layout.addWidget(self.food_combo, 1)
        
        self.add_food_btn = QPushButton("+ Add Food")
        self.add_food_btn.setFixedWidth(100)
        self.add_food_btn.setCursor(Qt.PointingHandCursor)
        self.add_food_btn.setStyleSheet("""
            QPushButton {
                background: #8b5cf6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #7c3aed;
            }
            QPushButton:pressed {
                background: #6d28d9;
            }
        """)
        self.add_food_btn.clicked.connect(self.add_food_item)
        add_food_layout.addWidget(self.add_food_btn)
        
        card_layout.addLayout(add_food_layout)
        
        layout.addWidget(card)
        
        # Card styling
        card.setStyleSheet("""
            #meal_card {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
            #meal_card:hover {
                border-color: #cbd5e1;
            }
        """)
    
    def load_foods_from_db(self):
        """Load available foods from database"""
        try:
            foods_data = get_all_foods()
            self.all_foods = foods_data
            self.food_combo.clear()
            self.food_combo.addItem("-- Select Food --", None)
            for food in foods_data:
                calories = food.get('calories_per_100g', 0)
                # Add category if available
                category = food.get('category', '')
                category_text = f" [{category}]" if category else ""
                self.food_combo.addItem(f"{self.get_food_icon_by_category(category)} {food['name']}{category_text} ({calories} kcal/100g)", food)
        except Exception as e:
            print(f"Error loading foods: {e}")
            self.food_combo.addItem("Error loading foods", None)
    
    def get_food_icon_by_category(self, category):
        """Return icon based on food category"""
        category = category.lower()
        if category == 'meat':
            return "🍗"
        elif category == 'fish':
            return "🐟"
        elif category == 'grains':
            return "🍚"
        elif category == 'fruit':
            return "🍎"
        elif category == 'vegetable':
            return "🥦"
        elif category == 'dairy':
            return "🥛"
        else:
            return "🍽️"
    
    def add_food_item(self, food_data=None, serving_size=1.0):
        """Add a food item to this meal"""
        if not food_data:
            index = self.food_combo.currentIndex()
            if index <= 0:
                QMessageBox.warning(self, "No Food Selected", "Please select a food item from the list.")
                return
            food_data = self.food_combo.itemData(index)
        
        if food_data:
            # Allow multiple servings of same food (no duplicate checking)
            food_item = FoodItemWidget(food_data, serving_size)
            food_item.remove_food.connect(self.remove_food_item)
            food_item.food_updated.connect(self.update_total_calories)
            self.foods.append(food_data)
            
            # Hide empty label and add food item
            self.empty_label.setVisible(False)
            self.foods_layout.addWidget(food_item)
            
            # Update total calories
            self.update_total_calories()
            self.meal_updated.emit()
    
    def remove_food_item(self, food_widget):
        """Remove a food item from this meal"""
        if hasattr(food_widget, 'food_data'):
            if food_widget.food_data in self.foods:
                self.foods.remove(food_widget.food_data)
        
        self.foods_layout.removeWidget(food_widget)
        food_widget.deleteLater()
        
        # Show empty label if no foods left
        if self.foods_layout.count() == 1:  # Only empty label remains
            self.empty_label.setVisible(True)
        
        # Update total calories
        self.update_total_calories()
        self.meal_updated.emit()
    
    def update_total_calories(self):
        """Calculate and update total calories for the meal"""
        total_calories = 0
        for i in range(self.foods_layout.count()):
            widget = self.foods_layout.itemAt(i).widget()
            if widget and isinstance(widget, FoodItemWidget):
                # Get calories based on serving size
                calories_per_100g = widget.food_data.get('calories_per_100g', 0)
                total_calories += calories_per_100g * widget.serving_size
        
        self.total_calories_label.setText(f"{total_calories:.0f} kcal total")
        
        # Change color based on calorie range
        if total_calories > 800:
            self.total_calories_label.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: 600; margin-left: 10px;")
        elif total_calories > 400:
            self.total_calories_label.setStyleSheet("color: #f59e0b; font-size: 12px; font-weight: 600; margin-left: 10px;")
        else:
            self.total_calories_label.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 600; margin-left: 10px;")
    
    def get_meal_data(self):
        """Get meal data for saving"""
        foods_with_servings = []
        for i in range(self.foods_layout.count()):
            widget = self.foods_layout.itemAt(i).widget()
            if widget and isinstance(widget, FoodItemWidget):
                food_copy = widget.food_data.copy()
                food_copy['serving_size'] = widget.serving_size
                food_copy['calories'] = widget.food_data.get('calories_per_100g', 0) * widget.serving_size
                foods_with_servings.append(food_copy)
        
        return {
            "name": self.meal_name,
            "foods": foods_with_servings
        }


class RecordItem(QWidget):
    record_changed = Signal()
    
    def __init__(self, record_id, title, description, record_type, due_date, is_done=False, 
                 intensity="Medium", exercise_name="", meals_data=None):
        super().__init__()
        self.record_id = record_id
        self.title = title
        self.description = description
        self.record_type = record_type
        self.due_date = due_date
        self.is_done = is_done
        self.intensity = intensity
        self.exercise_name = exercise_name
        self.meals_data = meals_data or []
        self.setup_ui()
    
    def __del__(self):
        """Ensure signals are disconnected when object is destroyed"""
        try:
            self.record_changed.disconnect()
        except:
            pass
    
    def setup_ui(self):
        self.setObjectName("record_item")
        self.setMinimumHeight(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Main card
        card = QWidget()
        card.setObjectName("record_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(8)
        
        # Top section
        top_section = QHBoxLayout()
        top_section.setSpacing(12)
        
        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.is_done)
        self.checkbox.setCursor(Qt.PointingHandCursor)
        self.checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
                border-radius: 11px;
                border: 2px solid #cbd5e1;
                background: white;
            }
            QCheckBox::indicator:hover {
                border-color: #94a3b8;
            }
            QCheckBox::indicator:checked {
                background: #10b981;
                border-color: #10b981;
            }
        """)
        self.checkbox.toggled.connect(self.on_toggle)
        top_section.addWidget(self.checkbox)
        
        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(6)
        
        # Title and badges row
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        
        # Type badge
        if self.record_type == "workout":
            badge_bg = "#dbeafe"
            badge_color = "#1e40af"
            badge_icon = "🏋️"
            badge_text = "Workout"
        else:
            badge_bg = "#ede9fe"
            badge_color = "#5b21b6"
            badge_icon = "🍽️"
            badge_text = "Diet"
        
        self.badge = QLabel(f"{badge_icon} {badge_text}")
        self.badge.setStyleSheet(f"""
            background: {badge_bg};
            color: {badge_color};
            padding: 3px 10px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
        """)
        title_row.addWidget(self.badge)
        
        # Intensity badge for workouts
        if self.record_type == "workout" and self.intensity:
            intensity_styles = {
                "Low": ("#d1fae5", "#065f46"),
                "Medium": ("#fed7aa", "#9a3412"),
                "High": ("#fee2e2", "#991b1b")
            }
            bg, color = intensity_styles.get(self.intensity, ("#f1f5f9", "#475569"))
            
            self.intensity_badge = QLabel(f"⚡ {self.intensity}")
            self.intensity_badge.setStyleSheet(f"""
                background: {bg};
                color: {color};
                padding: 3px 10px;
                border-radius: 10px;
                font-size: 11px;
                font-weight: 600;
            """)
            title_row.addWidget(self.intensity_badge)
        
        # Title
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.title_label.setStyleSheet("color: #0f172a;")
        title_row.addWidget(self.title_label)
        title_row.addStretch()
        
        content_layout.addLayout(title_row)
        
        # Description
        if self.description:
            self.desc_label = QLabel(self.description)
            self.desc_label.setWordWrap(True)
            self.desc_label.setStyleSheet("color: #64748b; font-size: 12px; line-height: 1.4;")
            content_layout.addWidget(self.desc_label)
        
        # Exercise name (workout)
        if self.record_type == "workout" and self.exercise_name:
            exercise_row = QHBoxLayout()
            exercise_row.setSpacing(6)
            exercise_icon = QLabel("🎯")
            exercise_icon.setStyleSheet("font-size: 12px;")
            exercise_row.addWidget(exercise_icon)
            
            self.exercise_label = QLabel(self.exercise_name)
            self.exercise_label.setStyleSheet("color: #64748b; font-size: 11px;")
            exercise_row.addWidget(self.exercise_label)
            exercise_row.addStretch()
            content_layout.addLayout(exercise_row)
        
        # Meals summary (diet)
        if self.record_type == "diet" and self.meals_data:
            meals_summary = QWidget()
            meals_summary_layout = QVBoxLayout(meals_summary)
            meals_summary_layout.setContentsMargins(0, 4, 0, 0)
            meals_summary_layout.setSpacing(4)
            
            for meal in self.meals_data:
                if meal.get('foods'):
                    meal_row = QHBoxLayout()
                    meal_row.setSpacing(6)
                    
                    meal_icon = QLabel("🍽️")
                    meal_icon.setStyleSheet("font-size: 11px;")
                    meal_row.addWidget(meal_icon)
                    
                    meal_name = QLabel(f"{meal['name']}:")
                    meal_name.setStyleSheet("color: #475569; font-size: 11px; font-weight: 600;")
                    meal_row.addWidget(meal_name)
                    
                    food_names = []
                    total_cal = 0
                    for food in meal['foods']:
                        serving = food.get('serving_size', 1)
                        food_names.append(f"{food['name']} ({serving}x)")
                        total_cal += food.get('calories_per_100g', 0) * serving
                    
                    meal_details = QLabel(f"{', '.join(food_names)} - {total_cal:.0f} kcal")
                    meal_details.setStyleSheet("color: #94a3b8; font-size: 11px;")
                    meal_row.addWidget(meal_details)
                    meal_row.addStretch()
                    
                    meals_summary_layout.addLayout(meal_row)
            
            content_layout.addWidget(meals_summary)
        
        # Due date
        date_row = QHBoxLayout()
        date_row.setSpacing(6)
        date_icon = QLabel("📅")
        date_icon.setStyleSheet("font-size: 11px;")
        date_row.addWidget(date_icon)
        
        self.date_label = QLabel(self.due_date)
        self.date_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        date_row.addWidget(self.date_label)
        date_row.addStretch()
        content_layout.addLayout(date_row)
        
        top_section.addLayout(content_layout, 1)
        
        # Action buttons
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)
        
        edit_btn = QPushButton("✏️")
        edit_btn.setFixedSize(36, 36)
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setToolTip("Edit record")
        edit_btn.setStyleSheet("""
            QPushButton {
                background: #f1f5f9;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #e2e8f0;
            }
        """)
        edit_btn.clicked.connect(self.on_edit)
        actions_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️")
        delete_btn.setFixedSize(36, 36)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setToolTip("Delete record")
        delete_btn.setStyleSheet("""
            QPushButton {
                background: #fef2f2;
                border: 1px solid #fee2e2;
                border-radius: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #fee2e2;
            }
        """)
        delete_btn.clicked.connect(self.on_delete)
        actions_layout.addWidget(delete_btn)
        
        top_section.addLayout(actions_layout)
        
        card_layout.addLayout(top_section)
        main_layout.addWidget(card)
        
        # Card styling
        card.setStyleSheet("""
            #record_card {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
            #record_card:hover {
                border-color: #cbd5e1;
            }
        """)
        
        # Apply done styling if needed
        if self.is_done:
            self.apply_done_style()
    
    def apply_done_style(self):
        opacity = "0.6"
        self.title_label.setStyleSheet(f"color: #94a3b8; text-decoration: line-through; opacity: {opacity};")
        if hasattr(self, 'desc_label'):
            self.desc_label.setStyleSheet(f"color: #cbd5e1; font-size: 12px; opacity: {opacity};")
        if hasattr(self, 'exercise_label'):
            self.exercise_label.setStyleSheet(f"color: #cbd5e1; font-size: 11px; opacity: {opacity};")
    
    def on_toggle(self, checked):
        self.is_done = checked
        try:
            update_record(self.record_id, is_done=checked)
        except Exception as e:
            print(f"Error updating record status: {e}")
        
        if checked:
            self.apply_done_style()
        else:
            self.title_label.setStyleSheet("color: #0f172a;")
            if hasattr(self, 'desc_label'):
                self.desc_label.setStyleSheet("color: #64748b; font-size: 12px;")
            if hasattr(self, 'exercise_label'):
                self.exercise_label.setStyleSheet("color: #64748b; font-size: 11px;")
        
        self.record_changed.emit()
    
    def on_edit(self):
        dialog = RecordDialog(self.record_id, self.title, self.description, 
                            self.record_type, self.due_date, self.intensity, 
                            self.exercise_name, self.meals_data)
        dialog.record_saved.connect(self.update_record)
        result = dialog.exec()
        dialog.deleteLater()  # Ensure dialog is cleaned up
    
    def on_delete(self):
        reply = QMessageBox.question(
            self, "Delete Record",
            f"Are you sure you want to delete '{self.title}'?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                delete_record(self.record_id)
            except Exception as e:
                print(f"Error deleting record: {e}")
            
            # Emit change and let parent handle removal
            self.record_changed.emit()
    
    def update_record(self, title, description, record_type, due_date, 
                    intensity="Medium", exercise_name="", meals_data=None):
        try:
            update_record(
                self.record_id, 
                title=title, 
                description=description,
                record_type=record_type, 
                due_date=due_date,
                intensity=intensity, 
                exercise_name=exercise_name
            )
        except Exception as e:
            print(f"Error updating record: {e}")
        
        self.title = title
        self.description = description
        self.record_type = record_type
        self.due_date = due_date
        self.intensity = intensity
        self.exercise_name = exercise_name
        self.meals_data = meals_data or []
        
        # Rebuild the widget completely
        old_layout = self.layout()
        if old_layout:
            QWidget().setLayout(old_layout)
        
        self.setup_ui()
        self.record_changed.emit()


class RecordDialog(QDialog):
    """Modern dialog for adding/editing records"""
    
    record_saved = Signal(str, str, str, str, str, str, list)
    
    def __init__(self, record_id=None, title="", description="", record_type="workout", 
                 due_date="", intensity="Medium", exercise_name="", meals_data=None):
        super().__init__()
        self.record_id = record_id
        self.all_exercises = []
        self.meals_data = meals_data or []
        self.setWindowTitle("Edit Record" if record_id else "Add New Record")
        self.setMinimumSize(700, 750)
        self.setup_ui(title, description, record_type, due_date, intensity, exercise_name)
        self.load_exercises()
        self.apply_styles()
    
    def load_exercises(self):
        try:
            from database.exercise import get_all_exercises
            exercises_data = get_all_exercises()
            self.all_exercises = [ex["name"] for ex in exercises_data]
            self.exercise_combo.clear()
            self.exercise_combo.addItem("-- Select Exercise --", "")
            for exercise_name in self.all_exercises:
                self.exercise_combo.addItem(exercise_name, exercise_name)
        except Exception as e:
            print(f"Error loading exercises: {e}")
    
    def setup_ui(self, title, description, record_type, due_date, intensity, exercise_name):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Main container with padding
        container = QWidget()
        container.setObjectName("dialog_container")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(28, 28, 28, 20)
        container_layout.setSpacing(20)
        
        # Header
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        
        icon_label = QLabel("📝")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 40px;")
        header_layout.addWidget(icon_label)
        
        title_label = QLabel("Record Details")
        title_label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #0f172a;")
        header_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Add your workout or meal plan details")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #94a3b8; font-size: 13px;")
        header_layout.addWidget(subtitle_label)
        
        container_layout.addWidget(header_widget)
        
        # Separator
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background: #e2e8f0;")
        container_layout.addWidget(separator)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(16)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        # Form section
        form_widget = QWidget()
        form_widget.setObjectName("form_widget")
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(14)
        form_layout.setLabelAlignment(Qt.AlignRight)
        
        # Record type with visual toggle
        self.type_combo = QComboBox()
        self.type_combo.addItems(["🏋️ Workout", "🍽️ Diet"])
        self.type_combo.setCurrentIndex(0 if record_type == "workout" else 1)
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        self.type_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 500;
                background: white;
                min-width: 200px;
            }
            QComboBox:hover {
                border-color: #cbd5e1;
            }
            QComboBox:focus {
                border-color: #8b5cf6;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
        """)
        form_layout.addRow("Type:", self.type_combo)
        
        # Title
        self.title_input = QLineEdit()
        self.title_input.setText(title)
        self.title_input.setPlaceholderText("e.g., Morning Run, High Protein Lunch")
        form_layout.addRow("Title:", self.title_input)
        
        # Exercise (workout)
        self.exercise_combo = QComboBox()
        self.exercise_combo.setEditable(True)
        self.exercise_combo.addItem("-- Select Exercise --", "")
        form_layout.addRow("Exercise:", self.exercise_combo)
        
        # Intensity (workout)
        self.intensity_combo = QComboBox()
        self.intensity_combo.addItems(["Low", "Medium", "High"])
        self.intensity_combo.setCurrentText(intensity)
        form_layout.addRow("Intensity:", self.intensity_combo)
        
        # Description
        self.desc_input = QTextEdit()
        self.desc_input.setPlainText(description)
        self.desc_input.setPlaceholderText("Add details about your workout or meal plan...")
        self.desc_input.setMaximumHeight(90)
        form_layout.addRow("Description:", self.desc_input)
        
        # Due date
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        if due_date:
            try:
                date = QDate.fromString(due_date, "MMM dd, yyyy")
                self.date_input.setDate(date)
            except:
                pass
        form_layout.addRow("Due Date:", self.date_input)
        
        scroll_layout.addWidget(form_widget)
        
        # Workout section
        self.workout_section = QWidget()
        self.workout_section.setObjectName("workout_section")
        workout_layout = QVBoxLayout(self.workout_section)
        workout_layout.setContentsMargins(0, 8, 0, 8)
        workout_layout.setSpacing(12)
        
        workout_header = QLabel("💪 Workout Tips")
        workout_header.setFont(QFont("Segoe UI", 13, QFont.Bold))
        workout_header.setStyleSheet("color: #0f172a;")
        workout_layout.addWidget(workout_header)
        
        workout_tips = QLabel(
            "• Choose appropriate exercises for your fitness level\n"
            "• Start with a warm-up and end with a cool-down\n"
            "• Stay hydrated during your workout\n"
            "• Track your progress over time"
        )
        workout_tips.setStyleSheet("color: #64748b; font-size: 12px; line-height: 1.6;")
        workout_layout.addWidget(workout_tips)
        
        scroll_layout.addWidget(self.workout_section)
        
        # Diet section with meals
        self.diet_section = QWidget()
        self.diet_section.setObjectName("diet_section")
        diet_layout = QVBoxLayout(self.diet_section)
        diet_layout.setContentsMargins(0, 8, 0, 8)
        diet_layout.setSpacing(16)
        
        # Meals header
        meals_header = QHBoxLayout()
        meals_title = QLabel("🍽️ Meal Plan")
        meals_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        meals_title.setStyleSheet("color: #0f172a;")
        meals_header.addWidget(meals_title)
        
        meals_header.addStretch()
        
        add_meal_btn = QPushButton("+ Add Meal")
        add_meal_btn.setFixedSize(110, 34)
        add_meal_btn.setCursor(Qt.PointingHandCursor)
        add_meal_btn.setStyleSheet("""
            QPushButton {
                background: #8b5cf6;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #7c3aed;
            }
        """)
        add_meal_btn.clicked.connect(self.add_meal)
        meals_header.addWidget(add_meal_btn)
        
        diet_layout.addLayout(meals_header)
        
        # Meals container
        self.meals_container = QWidget()
        self.meals_container_layout = QVBoxLayout(self.meals_container)
        self.meals_container_layout.setContentsMargins(0, 0, 0, 0)
        self.meals_container_layout.setSpacing(14)
        
        diet_layout.addWidget(self.meals_container)
        
        scroll_layout.addWidget(self.diet_section)
        
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        container_layout.addWidget(scroll, 1)
        
        # Separator
        separator2 = QWidget()
        separator2.setFixedHeight(1)
        separator2.setStyleSheet("background: #e2e8f0;")
        container_layout.addWidget(separator2)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(42)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #f1f5f9;
                border: 1px solid #e2e8f0;
                color: #475569;
                border-radius: 10px;
                font-weight: 600;
                font-size: 13px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background: #e2e8f0;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        btn_layout.addStretch()
        
        save_btn = QPushButton("Save Record")
        save_btn.setFixedHeight(42)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background: #4f46e5;
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: 600;
                font-size: 13px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background: #4338ca;
            }
        """)
        save_btn.clicked.connect(self.on_save)
        btn_layout.addWidget(save_btn)
        
        container_layout.addLayout(btn_layout)
        main_layout.addWidget(container)
        
        # Set initial state
        self.on_type_changed(self.type_combo.currentIndex())
        
        # Set initial exercise
        if exercise_name:
            idx = self.exercise_combo.findText(exercise_name)
            if idx >= 0:
                self.exercise_combo.setCurrentIndex(idx)
        
        # Load meals
        if record_type == "diet":
            if self.meals_data:
                self.load_existing_meals()
            else:
                # Add 3 default meals
                for i in range(3):
                    self.add_meal()
    
    def on_type_changed(self, index):
        is_workout = (index == 0)
        
        self.workout_section.setVisible(is_workout)
        self.diet_section.setVisible(not is_workout)
        
        # Toggle form fields
        form_layout = self.findChild(QFormLayout)
        if form_layout:
            for row in range(form_layout.rowCount()):
                label_item = form_layout.itemAt(row, QFormLayout.LabelRole)
                if label_item and label_item.widget():
                    label = label_item.widget()
                    if isinstance(label, QLabel):
                        if "Exercise:" in label.text() or "Intensity:" in label.text():
                            form_layout.setRowVisible(row, is_workout)
        
        # Add default meals when switching to diet
        if not is_workout and self.meals_container_layout.count() == 0:
            for i in range(3):
                self.add_meal()
    
    def add_meal(self):
        meal_number = self.meals_container_layout.count() + 1
        meal_name = f"Meal {meal_number}"
        
        existing_names = []
        for i in range(self.meals_container_layout.count()):
            widget = self.meals_container_layout.itemAt(i).widget()
            if widget and isinstance(widget, MealWidget):
                existing_names.append(widget.meal_name)
        
        while meal_name in existing_names:
            meal_number += 1
            meal_name = f"Meal {meal_number}"
        
        meal_widget = MealWidget(meal_name)
        meal_widget.remove_meal_btn.clicked.connect(
            lambda checked=False, mw=meal_widget: self.remove_meal(mw)
        )
        self.meals_container_layout.addWidget(meal_widget)
    
    def remove_meal(self, meal_widget):
        if self.meals_container_layout.count() > 3:
            self.meals_container_layout.removeWidget(meal_widget)
            meal_widget.deleteLater()
            
            # Rename remaining meals
            for i in range(self.meals_container_layout.count()):
                widget = self.meals_container_layout.itemAt(i).widget()
                if widget and isinstance(widget, MealWidget):
                    widget.meal_label.setText(f"Meal {i + 1}")
                    widget.meal_name = f"Meal {i + 1}"
        else:
            QMessageBox.information(
                self, "Minimum Meals", 
                "At least 3 meals are required.\nYou can add more foods to existing meals."
            )
    
    def load_existing_meals(self):
        for meal_data in self.meals_data:
            meal_widget = MealWidget(meal_data.get('name', f"Meal {self.meals_container_layout.count() + 1}"))
            meal_widget.remove_meal_btn.clicked.connect(
                lambda checked=False, mw=meal_widget: self.remove_meal(mw)
            )
            self.meals_container_layout.addWidget(meal_widget)
            
            for food_data in meal_data.get('foods', []):
                serving_size = food_data.get('serving_size', 1.0)
                meal_widget.add_food_item(food_data, serving_size)
    
    def on_save(self):
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Missing Title", "Please enter a title for your record.")
            self.title_input.setFocus()
            return
        
        record_type = "workout" if self.type_combo.currentIndex() == 0 else "diet"
        description = self.desc_input.toPlainText().strip()
        due_date = self.date_input.date().toString("MMM dd, yyyy")
        intensity = self.intensity_combo.currentText() if record_type == "workout" else "Medium"
        exercise_name = self.exercise_combo.currentText() if record_type == "workout" else ""
        
        # Collect meals
        meals_data = []
        if record_type == "diet":
            for i in range(self.meals_container_layout.count()):
                meal_widget = self.meals_container_layout.itemAt(i).widget()
                if meal_widget and isinstance(meal_widget, MealWidget):
                    meal_data = meal_widget.get_meal_data()
                    if meal_data['foods']:
                        meals_data.append(meal_data)
            
            if not meals_data:
                reply = QMessageBox.question(
                    self, "No Foods Added",
                    "You haven't added any foods to your meals.\nSave anyway?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
        
        self.record_saved.emit(title, description, record_type, due_date, 
                              intensity, exercise_name, meals_data)
        self.accept()
    
    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background: #f8fafc;
            }
            #dialog_container {
                background: white;
                border-radius: 16px;
            }
            QLineEdit, QTextEdit, QDateEdit {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                background: white;
            }
            QLineEdit:focus, QTextEdit:focus, QDateEdit:focus {
                border-color: #8b5cf6;
                background: #faf5ff;
            }
            QLineEdit:hover, QTextEdit:hover, QDateEdit:hover {
                border-color: #cbd5e1;
            }
            QLabel {
                color: #334155;
                font-size: 13px;
            }
        """)


class RecordsPage(QWidget):
    records_changed = Signal() 
    def __init__(self, user_id=None):
        super().__init__()
        self.user_id = user_id
        self.records = []
        self.setup_ui()
        self.load_records()

        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Container
        container = QWidget()
        container.setObjectName("page_container")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(32, 28, 32, 28)
        container_layout.setSpacing(24)
        
        # Header
        header = QHBoxLayout()
        
        header_text = QVBoxLayout()
        header_text.setSpacing(4)
        
        page_title = QLabel("📋 My Records")
        page_title.setFont(QFont("Segoe UI", 26, QFont.Bold))
        page_title.setStyleSheet("color: #0f172a;")
        header_text.addWidget(page_title)
        
        page_subtitle = QLabel("Track your workouts and meal plans")
        page_subtitle.setStyleSheet("color: #94a3b8; font-size: 14px;")
        header_text.addWidget(page_subtitle)
        
        header.addLayout(header_text)
        header.addStretch()
        
        # Add button
        add_btn = QPushButton("+ New Record")
        add_btn.setFixedSize(150, 44)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton {
                background: #4f46e5;
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #4338ca;
            }
            QPushButton:pressed {
                background: #3730a3;
            }
        """)
        add_btn.clicked.connect(self.add_record)
        header.addWidget(add_btn)
        
        container_layout.addLayout(header)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
            QTabBar::tab {
                padding: 10px 28px;
                font-size: 14px;
                font-weight: 500;
                color: #64748b;
                border: none;
                border-bottom: 2px solid transparent;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                color: #4f46e5;
                border-bottom: 2px solid #4f46e5;
            }
            QTabBar::tab:hover {
                color: #4338ca;
            }
        """)
        
        # Active tab
        self.active_tab = QWidget()
        active_layout = QVBoxLayout(self.active_tab)
        active_layout.setContentsMargins(0, 16, 0, 0)
        active_layout.setSpacing(0)
        
        self.active_scroll = QScrollArea()
        self.active_scroll.setWidgetResizable(True)
        self.active_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.active_widget = QWidget()
        self.active_layout = QVBoxLayout(self.active_widget)
        self.active_layout.setAlignment(Qt.AlignTop)
        self.active_layout.setSpacing(10)
        self.active_layout.setContentsMargins(0, 0, 0, 0)
        
        self.active_empty = QLabel("No active records yet. 🎯\nClick '+ New Record' to get started!")
        self.active_empty.setAlignment(Qt.AlignCenter)
        self.active_empty.setStyleSheet("color: #94a3b8; font-size: 15px; padding: 60px; line-height: 1.6;")
        self.active_empty.setVisible(False)
        self.active_layout.addWidget(self.active_empty)
        
        self.active_scroll.setWidget(self.active_widget)
        active_layout.addWidget(self.active_scroll)
        
        # Completed tab
        self.completed_tab = QWidget()
        completed_layout = QVBoxLayout(self.completed_tab)
        completed_layout.setContentsMargins(0, 16, 0, 0)
        completed_layout.setSpacing(0)
        
        self.completed_scroll = QScrollArea()
        self.completed_scroll.setWidgetResizable(True)
        self.completed_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.completed_widget = QWidget()
        self.completed_layout = QVBoxLayout(self.completed_widget)
        self.completed_layout.setAlignment(Qt.AlignTop)
        self.completed_layout.setSpacing(10)
        self.completed_layout.setContentsMargins(0, 0, 0, 0)
        
        self.completed_empty = QLabel("No completed records yet. ✅\nComplete your active records to see them here.")
        self.completed_empty.setAlignment(Qt.AlignCenter)
        self.completed_empty.setStyleSheet("color: #94a3b8; font-size: 15px; padding: 60px; line-height: 1.6;")
        self.completed_empty.setVisible(False)
        self.completed_layout.addWidget(self.completed_empty)
        
        self.completed_scroll.setWidget(self.completed_widget)
        completed_layout.addWidget(self.completed_scroll)
        
        self.tab_widget.addTab(self.active_tab, "📋 Active")
        self.tab_widget.addTab(self.completed_tab, "✅ Completed")
        
        container_layout.addWidget(self.tab_widget, 1)
        main_layout.addWidget(container)
        
        # Page styling
        container.setStyleSheet("""
            #page_container {
                background: #f8fafc;
                border-radius: 16px;
            }
        """)
    
    def add_record(self, record_data=None):
        if record_data:
            title = record_data.get("title", "Untitled")
            description = record_data.get("description", "")
            record_type = record_data.get("type", "workout")
            due_date = record_data.get("due_date", QDate.currentDate().toString("MMM dd, yyyy"))
            intensity = record_data.get("intensity", "Medium")
            exercise_name = record_data.get("exercise_name", "")
            meals_data = record_data.get("meals_data", [])
            self.save_new_record(title, description, record_type, due_date, intensity, exercise_name, meals_data)
        else:
            dialog = RecordDialog()
            dialog.record_saved.connect(self.save_new_record)
            dialog.exec()
    
    def set_user_id(self, user_id):
        self.user_id = user_id
        if user_id:
            self.records.clear()
            self.load_records()
        else:
            self.records.clear()
            self.refresh_lists()
    
    def save_new_record(self, title, description, record_type, due_date, intensity="Medium", exercise_name="", meals_data=None):
        if not self.user_id:
            QMessageBox.warning(self, "Error", "Please log in first to save records.")
            return
        
        try:
            # Your save_record only accepts 7 parameters (no meals_data)
            # So for diet records, we just save without meals_data
            record_id = save_record(
                self.user_id,
                title,
                description,
                record_type,
                due_date,
                intensity,
                exercise_name
            )
            
            if record_id:
                record = RecordItem(record_id, title, description, record_type, 
                                due_date, False, intensity, exercise_name, meals_data)
                record.record_changed.connect(self.on_records_changed)
                self.records.append(record)
                self.records_changed.emit()

                self.refresh_lists()
            else:
                QMessageBox.warning(self, "Error", "Failed to save record.")
        except Exception as e:
            print(f"Error saving record: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save record: {str(e)}")
    
    def on_records_changed(self):
        """Reload records from database and refresh UI."""
        self.load_records()
    
    def refresh_lists(self):
        """Reattach all record widgets to the correct tabs without deleting."""
        # Clear layouts without deleting widgets
        while self.active_layout.count():
            w = self.active_layout.takeAt(0).widget()
            if w and w != self.active_empty:
                w.setParent(None)  # Detach from layout but keep alive
        
        while self.completed_layout.count():
            w = self.completed_layout.takeAt(0).widget()
            if w and w != self.completed_empty:
                w.setParent(None)
        
        # Now re-add widgets in correct order
        active_count = 0
        completed_count = 0
        
        for record in self.records:
            if record.is_done:
                self.completed_layout.insertWidget(
                    max(0, self.completed_layout.count() - 1), record
                )
                completed_count += 1
            else:
                self.active_layout.insertWidget(
                    max(0, self.active_layout.count() - 1), record
                )
                active_count += 1
        
        self.active_empty.setVisible(active_count == 0)
        self.completed_empty.setVisible(completed_count == 0)
    
    def load_records(self):
        """Clear and reload all records from database."""
        if not self.user_id:
            self.records.clear()
            self.refresh_lists()
            return
        
        try:
            records_data = get_user_records(self.user_id)
            # Clear existing records to avoid duplicate widgets
            for rec in self.records:
                rec.deleteLater()  # schedule deletion of old widgets
            self.records.clear()
            
            for item in records_data:
                # parse meals, metadata...
                meals = item.get("meals_data", [])
                if isinstance(meals, str):
                    try:
                        meals = json.loads(meals)
                    except:
                        meals = []
                
                intensity = item.get("intensity", "Medium")
                exercise_name = item.get("exercise_name", "")
                metadata = item.get("metadata", {})
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                        intensity = metadata.get("intensity", intensity)
                        exercise_name = metadata.get("exercise_name", exercise_name)
                        if not meals and metadata.get("meals_data"):
                            meals = metadata.get("meals_data", [])
                    except:
                        pass
                
                record = RecordItem(
                    item["id"], item["title"], item["description"],
                    item["record_type"], item["due_date"], item["is_done"],
                    intensity, exercise_name, meals
                )
                record.record_changed.connect(self.on_records_changed)
                self.records.append(record)
            
            self.refresh_lists()
            
        except Exception as e:
            print(f"Error loading records: {e}")
            self.refresh_lists()
    
    def add_plan_from_llm(self, plan_data):
        self.add_record(plan_data)
        QMessageBox.information(self, "Plan Added", "New plan has been added to your records!")
    
    def get_active_records(self):
        return [{
            "title": r.title,
            "description": r.description,
            "type": r.record_type,
            "due_date": r.due_date,
            "intensity": getattr(r, 'intensity', 'Medium'),
            "exercise_name": getattr(r, 'exercise_name', ''),
            "meals_data": getattr(r, 'meals_data', [])
        } for r in self.records if not r.is_done]