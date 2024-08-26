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

def get_conversion_root_bone_name(context, rig_object):
    properties = context.scene.action_organizer
    return next(x.rig_root_name for x in properties.rig_conversion_properties if x.rig_object == rig_object)

def get_conversion_mesh(context, rig_object):
    properties = context.scene.action_organizer
    return next(x.mesh_object for x in properties.rig_conversion_properties if x.rig_object == rig_object)

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

def poll_mesh_object(self, object):
    return object.type == "MESH"

class ActionAssignmentProperty(bpy.types.PropertyGroup):
    action: bpy.props.PointerProperty(type=bpy.types.Action)
    assigned_rig_object: bpy.props.PointerProperty(type=bpy.types.Object, poll=poll_rig_object)

class ActionGroupProperty(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    action_assignments: bpy.props.CollectionProperty(type=ActionAssignmentProperty)

class RigConversionProperty(bpy.types.PropertyGroup):
    rig_object: bpy.props.PointerProperty(type=bpy.types.Object, poll=poll_rig_object)
    rig_root_name: bpy.props.StringProperty(default="root")
    mesh_object: bpy.props.PointerProperty(type=bpy.types.Object, poll=poll_mesh_object)

class ActionOrganizerProperties(bpy.types.PropertyGroup):
    action_groups: bpy.props.CollectionProperty(type=ActionGroupProperty)
    active_action_group_index: bpy.props.IntProperty()
    rig_conversion_properties: bpy.props.CollectionProperty(type=RigConversionProperty)

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
            self.poll_message_set(f"Can not convert action groups if action converter addon is not enabled")
            return False
        
        # Check that group index is valid.
        properties = context.scene.action_organizer
        group_count = len(properties.action_groups)
        index = properties.active_action_group_index
        if group_count < 1 or index < 0 or index >= group_count:
            self.poll_message_set(f"Active group index is invalid. Group index: {index}, total groups: {group_count}")
            return False
    
        action_group = properties.action_groups[index]
        for action_assignment in action_group.action_assignments:
            rig_object = action_assignment.assigned_rig_object

            # Check that root bones exist in the armature.
            rig_root_name = get_conversion_root_bone_name(context, rig_object)
            if rig_root_name not in rig_object.data.bones:
                self.poll_message_set(f"Root bone \"{rig_root_name}\" could not be found in armature \"{rig_object.name}\"")
                return False
            
            # Check that conversion meshes exist as a child of the armature.
            mesh_to_convert = get_conversion_mesh(context, rig_object)
            if mesh_to_convert == None:
                self.poll_message_set(f"No mesh has been assigned to be converted with armature \"{rig_object.name}\"")
                return False
            if mesh_to_convert not in rig_object.children:
                self.poll_message_set(f"Mesh \"{mesh_to_convert.name}\" could not be found in the children of armature \"{rig_object.name}\"")
                return False

        return True

    def execute(self, context):
        properties = context.scene.action_organizer
        action_group = properties.action_groups[properties.active_action_group_index]
        
        if not context.mode == "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        # Set animation data for all rigs in the group.
        # This ensures that animations on different rigs that rely on each other bake correcly, which is basically the whole point of this addon.
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

            # Select the rig object that is being converted.
            bpy.ops.object.select_all(action="DESELECT")
            assigned_rig_object.select_set(True)
            context.view_layer.objects.active = assigned_rig_object

            # Select the mesh object that is being converted.
            mesh_to_convert = get_conversion_mesh(context, action_assignment.assigned_rig_object)
            mesh_to_convert.select_set(True)

            # Get the root bone used in the conversion.
            rig_root_name = get_conversion_root_bone_name(context, action_assignment.assigned_rig_object)

            # Set the action that is being converted.
            converter_properties = context.scene.rigify_converter
            converter_properties.included_actions.clear()
            action_property = converter_properties.included_actions.add()
            action_property.action = action
            action_property.frame_range_start = combined_frame_range[0]
            action_property.frame_range_end = combined_frame_range[1]

            bpy.ops.rigify_converter.convert(add_as_root_bone=rig_root_name)

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
            bone_property_column.prop(action_assignment, "rig_root_name", text="")

class ConvertAllActionGroupsOperator(bpy.types.Operator):
    bl_idname = "action_organizer.convert_all_action_groups"
    bl_label = "Convert all action groups"
    bl_description = "Convert all action groups"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(self, context):
        # This operator depends on the rigify converter addon being enabled.
        if not hasattr(bpy.ops.rigify_converter, "convert"):
            return False
        
        # Check that there is at least one action group.
        properties = context.scene.action_organizer
        return len(properties.action_groups) > 0

    def execute(self, context):
        properties = context.scene.action_organizer

        for i, action_group in enumerate(properties.action_groups):
            properties.active_action_group_index = i
            bpy.ops.action_organizer.convert_action_groups()
        
        return {"FINISHED"}
    
    def invoke(self, context, event):
        properties = context.scene.action_organizer

        group = properties.action_groups[properties.active_action_group_index]

        # Avoid clearing valid properties.
        saved_properties = {}
        assignment_rigs = [x.assigned_rig_object for x in group.action_assignments if x.assigned_rig_object]
        for property in properties.rig_conversion_properties:
            if property.rig_object != None and property.rig_object in assignment_rigs:
                saved_properties[property.rig_object.name] = {
                    "rig_root_name": property.rig_root_name,
                    "mesh_object": property.mesh_object,
                }

        # Clear and add rig conversion properties.
        properties.rig_conversion_properties.clear()
        for rig_object in (x.assigned_rig_object for x in group.action_assignments if x.assigned_rig_object != None):
            new_property = properties.rig_conversion_properties.add()
            new_property.rig_object = rig_object
            try:
                new_property.rig_root_name = saved_properties[rig_object.name]["rig_root_name"]
                new_property.mesh_object = saved_properties[rig_object.name]["mesh_object"]
            except:
                pass
        
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        properties = context.scene.action_organizer
        layout = self.layout

        # Label.
        box = layout.box()
        box.label(text="Root bones")

        # Create columns.
        row = box.row()
        bone_label_column = row.column()
        bone_label_column.alignment = "RIGHT"
        bone_property_column = row.column()
        mesh_property_column = row.column()

        # Add a row for each property.
        for rig_conversion_property in properties.rig_conversion_properties:
            if rig_conversion_property.rig_object != None:
                bone_label_column.label(text=rig_conversion_property.rig_object.name)
                bone_property_column.prop(rig_conversion_property, "rig_root_name", text="")
                mesh_property_column.prop_search(rig_conversion_property, "mesh_object", context.scene, "objects", text="")

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
    buttons_row.operator(ConvertAllActionGroupsOperator.bl_idname, text="Convert")

classes = (
    ACTION_ORGANIZER_UL_ActionGroup,
    ActionAssignmentProperty,
    ActionGroupProperty,
    RigConversionProperty,
    ActionOrganizerProperties,
    CreateActionGroupOperator,
    RemoveActionGroupOperator,
    CreateActionAssignmentOperator,
    RemoveActionAssignmentOperator,
    SelectActionAssignmentOperator,
    ActiveActionGroupSelectorOperator,
    ActionGroupEditorOperator,
    ConvertActionGroupOperator,
    ConvertAllActionGroupsOperator,
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
