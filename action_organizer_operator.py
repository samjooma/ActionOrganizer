import bpy
import os
import math

#
# Helper functions.
#

def active_group_index_is_valid(properties):
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
    if object.type != "ARMATURE":
        return False
    
    properties = bpy.context.scene.action_organizer
    if active_group_index_is_valid(properties):
        active_group = properties.action_groups[properties.active_action_group_index]
        if any(x for x in active_group.action_assignments if x.assigned_rig_object == object):
            return False
    
    return True

class ActionAssignmentProperty(bpy.types.PropertyGroup):
    action: bpy.props.PointerProperty(type=bpy.types.Action)
    assigned_rig_object: bpy.props.PointerProperty(type=bpy.types.Object, poll=poll_rig_object)
    rig_root_bone: bpy.props.StringProperty(default="root")

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
        properties = context.scene.action_organizer
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
        properties = context.scene.action_organizer
        return active_group_index_is_valid(properties)
    
    def execute(self, context):
        properties = context.scene.action_organizer
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
        properties = context.scene.action_organizer
        return active_group_index_is_valid(properties)

    def execute(self, context):
        properties = context.scene.action_organizer
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
        properties = context.scene.action_organizer
        return active_group_index_is_valid(properties)

    def execute(self, context):
        properties = context.scene.action_organizer
        group_index = properties.active_action_group_index
        action_group = properties.action_groups[group_index]
        action_group.action_assignments.remove(self.action_assignment_index)
        return {"FINISHED"}
    
class SelectActionAssignmentOperator(bpy.types.Operator):
    bl_idname = "action_organizer.select_action_assignment"
    bl_label = "Select action"
    bl_description = "Description"
    bl_options = {"REGISTER"}

    action_assignment_index: bpy.props.IntProperty()

    @classmethod
    def poll(self, context):
        properties = context.scene.action_organizer
        return active_group_index_is_valid(properties)

    def execute(self, context):
        properties = context.scene.action_organizer
        group_index = properties.active_action_group_index

        action_group = properties.action_groups[group_index]

        if not context.mode == "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        
        for i, action_assignment in enumerate(action_group.action_assignments):
            action = action_assignment.action
            assigned_rig_object = action_assignment.assigned_rig_object

            # Set action.
            if action != None:
                if assigned_rig_object.animation_data == None:
                    assigned_rig_object.animation_data_create()
                assigned_rig_object.animation_data.action = action

            # Select the rig.
            if i == self.action_assignment_index and assigned_rig_object != None:
                bpy.ops.object.select_all(action="DESELECT")
                assigned_rig_object.select_set(True)
                context.view_layer.objects.active = assigned_rig_object

        # Set mode to pose mode.
        bpy.ops.object.mode_set(mode="POSE")

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
        properties = context.scene.action_organizer
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
        properties = context.scene.action_organizer
        return active_group_index_is_valid(properties)
    
    def execute(self, context):
        return {"FINISHED"}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self)
    
    def draw(self, context):
        properties = context.scene.action_organizer

        layout = self.layout
        layout.ui_units_x = 25

        group_index = properties.active_action_group_index
        active_group = properties.action_groups[group_index]

        for action_assignment_index, action_assignment in enumerate(active_group.action_assignments):
            action_data_row = layout.row()

            # Button to select action and its assigned object.
            select_action_operator = action_data_row.operator(SelectActionAssignmentOperator.bl_idname, text="Select")
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

class ConvertActionGroupOperator(bpy.types.Operator):
    bl_idname = "action_organizer.convert_action_groups"
    bl_label = "Convert action group"
    bl_description = "Description"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(self, context):
        # This operator depends on the rigify converter addon being enabled.
        if not hasattr(bpy.ops.rigify_converter, "convert"):
            return False
        
        # Check that active group is valid.
        properties = context.scene.action_organizer
        group_count = len(properties.action_groups)
        index = properties.active_action_group_index
        return group_count > 0 and index > -1 and index < group_count

    def execute(self, context):
        properties = context.scene.action_organizer
        action_group = properties.action_groups[properties.active_action_group_index]

        # Check that root bones are valid.
        for action_assignment in action_group.action_assignments:
            bone_data = action_assignment.assigned_rig_object.data.bones
            try:
                bone_data[action_assignment.rig_root_bone]
            except:
                self.report({"ERROR"}, f"Couldn't find root bone \"{action_assignment.rig_root_bone}\" in armature \"{action_assignment.assigned_rig_object.name}\"")
                return {"CANCELLED"}
            
        if not context.mode == "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        # Set animation data for each armature in this group.
        for action_assignment in action_group.action_assignments:
            assigned_rig_object = action_assignment.assigned_rig_object
            action = action_assignment.action
            if action != None:
                if assigned_rig_object.animation_data == None:
                    assigned_rig_object.animation_data_create()
                assigned_rig_object.animation_data.action = action

        # Calculate the combined frame range from the beginning of the earliest action to the end of the latest action.
        combined_frame_range = (float("inf"), float("-inf"))
        for action_assignment in action_group.action_assignments:
            action = action_assignment.action
            frame_range = (math.floor(action.frame_range[0]), math.ceil(action.frame_range[1]))
            combined_frame_range = (
                min(combined_frame_range[0], frame_range[0]),
                max(combined_frame_range[1], frame_range[1]),
            )
        # Make frame range at least 2 frames long.
        combined_frame_range = (
            combined_frame_range[0],
            combined_frame_range[1] + 1 if combined_frame_range[0] == combined_frame_range[1] else combined_frame_range[1]
        )
            
        for action_assignment in action_group.action_assignments:
            assigned_rig_object = action_assignment.assigned_rig_object
            action = action_assignment.action
            rig_root_bone = action_assignment.rig_root_bone

            # Set object to be converted.
            bpy.ops.object.select_all(action="DESELECT")
            assigned_rig_object.select_set(True)
            context.view_layer.objects.active = assigned_rig_object

            # Set action to be converted.
            converter_properties = context.scene.rigify_converter
            converter_properties.included_actions.clear()
            action_property = converter_properties.included_actions.add()
            action_property.action = action
            action_property.frame_range_start = combined_frame_range[0]
            action_property.frame_range_end = combined_frame_range[1]

            bpy.ops.rigify_converter.convert(add_as_root_bone=rig_root_bone)

        return {"FINISHED"}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        properties = context.scene.action_organizer
        action_group = properties.action_groups[properties.active_action_group_index]

        layout = self.layout
        box = layout.box()
        box.label(text="Root bones")

        row = box.row()
        bone_label_column = row.column()
        bone_label_column.alignment = "RIGHT"
        bone_property_column = row.column()
        for action_assignment in action_group.action_assignments:
            bone_label_column.label(text=action_assignment.assigned_rig_object.name)
            bone_property_column.prop(action_assignment, "rig_root_bone", text="")

#
# Registration.
#

def menu_function(self, context):
    properties = context.scene.action_organizer
    layout = self.layout

    row = layout.row(align=True)

    # Button for selecting action group.
    row.ui_units_x = 10
    row.operator(ActiveActionGroupSelectorOperator.bl_idname, text="", icon="DOWNARROW_HLT")

    split = row.split(factor=0.6, align=True)

    if active_group_index_is_valid(properties):
        group_index = properties.active_action_group_index
        group = properties.action_groups[group_index]
        split.prop(group, "name", text="")
    else:
        split.operator(CreateActionGroupOperator.bl_idname, text="New")
    
    buttons_row = split.row(align=True)
    buttons_row.operator(ActionGroupEditorOperator.bl_idname, text="Edit")
    buttons_row.operator(ConvertActionGroupOperator.bl_idname, text="Convert")

classes = (
    ACTION_ORGANIZER_UL_ActionGroup,
    ActionAssignmentProperty,
    ActionGroupProperty,
    ActionOrganizerProperties,
    CreateActionGroupOperator,
    RemoveActionGroupOperator,
    CreateActionAssignmentOperator,
    RemoveActionAssignmentOperator,
    SelectActionAssignmentOperator,
    ActiveActionGroupSelectorOperator,
    ActionGroupEditorOperator,
    ConvertActionGroupOperator,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.action_organizer = bpy.props.PointerProperty(type=ActionOrganizerProperties)
    bpy.types.DOPESHEET_HT_header.append(menu_function)

def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
    del bpy.types.Scene.action_organizer
    bpy.types.DOPESHEET_HT_header.remove(menu_function)
