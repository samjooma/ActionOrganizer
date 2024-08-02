import bpy
import os

#
# Helper functions.
#

def action_group_index_is_valid(properties):
    group_count = len(properties.action_groups)
    index = properties.active_action_group_index
    return group_count > 0 and index >= 0 and index < group_count

#
# UI classes.
#

class ACTION_ORGANIZER_UL_ActionGroup(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {"DEFAULT", "COMPACT", "GRID"}:
            row = layout.row(align=True)
            row.alignment = "LEFT"
            row.label(text=item.name, icon_value=icon)

#
# Properties.
#

def poll_rig_object(self, object):
    return object.type == "ARMATURE"

class ActionAssignmentProperty(bpy.types.PropertyGroup):
    action: bpy.props.PointerProperty(type=bpy.types.Action)
    assigned_rig_object: bpy.props.PointerProperty(type=bpy.types.Object, poll=poll_rig_object)

class ActionGroupProperty(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    action_assignments: bpy.props.CollectionProperty(type=ActionAssignmentProperty)

class ActionOrganizerProperties(bpy.types.PropertyGroup):
    action_groups: bpy.props.CollectionProperty(type=ActionGroupProperty)
    active_action_group_index: bpy.props.IntProperty()

#
# Operators.
#

class CreateActionGroupOperator(bpy.types.Operator):
    bl_idname = "action_organizer.create_action_group"
    bl_label = "Create action group"
    bl_description = "Description"
    bl_options = {"REGISTER"}

    name: bpy.props.StringProperty(default="Action group")

    def execute(self, context):
        properties = context.window_manager.action_organizer
        new_group = properties.action_groups.add()
        new_group.name = self.name
        return {"FINISHED"}
    
class RemoveActionGroupOperator(bpy.types.Operator):
    bl_idname = "action_organizer.remove_action_group"
    bl_label = "Remove action group"
    bl_description = "Description"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(self, context):
        properties = context.window_manager.action_organizer
        return action_group_index_is_valid(properties)
    
    def execute(self, context):
        properties = context.window_manager.action_organizer
        index = properties.active_action_group_index
        properties.action_groups.remove(index)
        if properties.active_action_group_index >= index:
            properties.active_action_group_index = max(0, properties.active_action_group_index - 1)
        return {"FINISHED"}
    
class CreateActionAssignmentOperator(bpy.types.Operator):
    bl_idname = "action_organizer.create_action_assignment"
    bl_label = "Create action assignment"
    bl_description = "Description"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(self, context):
        properties = context.window_manager.action_organizer
        return action_group_index_is_valid(properties)

    def execute(self, context):
        properties = context.window_manager.action_organizer
        index = properties.active_action_group_index
        action_group = properties.action_groups[index]
        action_group.action_assignments.add()
        return {"FINISHED"}
    
class RemoveActionAssignmentOperator(bpy.types.Operator):
    bl_idname = "action_organizer.remove_action_from_group"
    bl_label = "Remove action from group"
    bl_description = "Description"
    bl_options = {"REGISTER"}

    action_assignment_index: bpy.props.IntProperty()

    @classmethod
    def poll(self, context):
        properties = context.window_manager.action_organizer
        return action_group_index_is_valid(properties)

    def execute(self, context):
        properties = context.window_manager.action_organizer
        group_index = properties.active_action_group_index
        action_group = properties.action_groups[group_index]
        action_group.action_assignments.remove(self.action_assignment_index)
        return {"FINISHED"}
    
class SelectActionInGroupOperator(bpy.types.Operator):
    bl_idname = "action_organizer.select_action_in_group"
    bl_label = "Select action"
    bl_description = "Description"
    bl_options = {"REGISTER"}

    action_assignment_index: bpy.props.IntProperty()

    @classmethod
    def poll(self, context):
        properties = context.window_manager.action_organizer
        return action_group_index_is_valid(properties)

    def execute(self, context):
        properties = context.window_manager.action_organizer
        group_index = properties.active_action_group_index
        action_group = properties.action_groups[group_index]
        action_assignment = action_group.action_assignments[self.action_assignment_index]

        action = action_assignment.action
        assigned_rig_object = action_assignment.assigned_rig_object

        if assigned_rig_object != None:
            if not context.mode == "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")

            # Select the new rig.
            bpy.ops.object.select_all(action="DESELECT")
            assigned_rig_object.select_set(True)
            context.view_layer.objects.active = assigned_rig_object

            # Set mode to pose mode.
            bpy.ops.object.mode_set(mode="POSE")

        if action != None:
            selected_objects = context.view_layer.objects.selected
            for rig_object in [x for x in selected_objects if x.type == "ARMATURE"]:
                if rig_object.animation_data == None:
                    rig_object.animation_data_create()
                rig_object.animation_data.action = action

        return {"FINISHED"}
    
class ActiveActionGroupSelectorOperator(bpy.types.Operator):
    bl_idname = "action_organizer.active_action_group_selector"
    bl_label = "Select active action group"
    bl_description = "Description"
    bl_options = {"REGISTER"}

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self)

    def execute(self, context):
        return {"FINISHED"}
    
    def draw(self, context):
        properties = context.window_manager.action_organizer
        layout = self.layout

        main_row = layout.row()

        main_row.template_list(
            listtype_name="ACTION_ORGANIZER_UL_ActionGroup",
            list_id="",
            dataptr=properties,
            propname="action_groups",
            active_dataptr=properties,
            active_propname="active_action_group_index",
            type="DEFAULT",
        )
        
        right_column = main_row.column(align=True)
        right_column.operator(CreateActionGroupOperator.bl_idname, text="", icon="ADD")
        right_column.operator(RemoveActionGroupOperator.bl_idname, text="", icon="REMOVE")

class ActionGroupEditorOperator(bpy.types.Operator):
    bl_idname = "action_organizer.action_group_editor"
    bl_label = "Edit action group"
    bl_description = "Description"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(self, context):
        properties = context.window_manager.action_organizer
        return action_group_index_is_valid(properties)
    
    def execute(self, context):
        return {"FINISHED"}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self)
    
    def draw(self, context):
        properties = context.window_manager.action_organizer

        layout = self.layout
        layout.ui_units_x = 25

        group_index = properties.active_action_group_index
        active_group = properties.action_groups[group_index]

        for action_assignment_index, action_assignment in enumerate(active_group.action_assignments):
            action_data_row = layout.row()

            # Button to select action and its assigned object.
            select_action_operator = action_data_row.operator(SelectActionInGroupOperator.bl_idname, text="Select")
            select_action_operator.action_assignment_index = action_assignment_index

            # Selection boxes for action and rig object.
            action_data_row.prop_search(action_assignment, "action", bpy.data, "actions", text="")
            action_data_row.prop_search(action_assignment, "assigned_rig_object", context.scene, "objects", text="")

            # Button to remove action assigment.
            remove_action_operator = action_data_row.operator(RemoveActionAssignmentOperator.bl_idname, text="", icon="REMOVE")
            remove_action_operator.action_assignment_index = action_assignment_index

        # Button to create a new action assigment.
        create_action_row = layout.row()
        create_action_row.operator(CreateActionAssignmentOperator.bl_idname, icon="ADD")

#
# Registration.
#

def menu_function(self, context):
    properties = context.window_manager.action_organizer
    layout = self.layout

    row = layout.row(align=True)

    # Button for selecting action group.
    row.ui_units_x = 10
    row.operator(ActiveActionGroupSelectorOperator.bl_idname, text="", icon="DOWNARROW_HLT")

    split = row.split(factor=0.75, align=True)

    if action_group_index_is_valid(properties):
        group_index = properties.active_action_group_index
        group = properties.action_groups[group_index]
        split.prop(group, "name", text="")
    else:
        split.operator(CreateActionGroupOperator.bl_idname, text="New")
    split.operator(ActionGroupEditorOperator.bl_idname, text="Edit")

classes = (
    ACTION_ORGANIZER_UL_ActionGroup,
    ActionAssignmentProperty,
    ActionGroupProperty,
    ActionOrganizerProperties,
    CreateActionGroupOperator,
    RemoveActionGroupOperator,
    CreateActionAssignmentOperator,
    RemoveActionAssignmentOperator,
    SelectActionInGroupOperator,
    ActiveActionGroupSelectorOperator,
    ActionGroupEditorOperator,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.WindowManager.action_organizer = bpy.props.PointerProperty(type=ActionOrganizerProperties)
    bpy.types.DOPESHEET_HT_header.append(menu_function)

def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
    del bpy.types.WindowManager.action_organizer
    bpy.types.DOPESHEET_HT_header.remove(menu_function)
