import bpy
import os

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
    is_expanded: bpy.props.BoolProperty(default=True)

class ActionOrganizerProperties(bpy.types.PropertyGroup):
    action_groups: bpy.props.CollectionProperty(type=ActionGroupProperty)

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

    action_group_index: bpy.props.IntProperty()

    def execute(self, context):
        properties = context.window_manager.action_organizer
        properties.action_groups.remove(self.action_group_index)
        return {"FINISHED"}
    
class ToggleActionGroupExpandedOperator(bpy.types.Operator):
    bl_idname = "action_organizer.toggle_action_group_expanded"
    bl_label = "Toggle action group expanded"
    bl_description = "Description"
    bl_options = {"REGISTER"}

    action_group_index: bpy.props.IntProperty()

    def execute(self, context):
        properties = context.window_manager.action_organizer
        action_group = properties.action_groups[self.action_group_index]
        action_group.is_expanded = not action_group.is_expanded
        return {"FINISHED"}
    
class CreateActionAssignmentOperator(bpy.types.Operator):
    bl_idname = "action_organizer.create_action_assignment"
    bl_label = "Create action assignment"
    bl_description = "Description"
    bl_options = {"REGISTER"}

    action_group_index: bpy.props.IntProperty()
    
    def execute(self, context):
        properties = context.window_manager.action_organizer
        action_group = properties.action_groups[self.action_group_index]
        action_group.action_assignments.add()
        return {"FINISHED"}
    
class RemoveActionAssignmentOperator(bpy.types.Operator):
    bl_idname = "action_organizer.remove_action_from_group"
    bl_label = "Remove action from group"
    bl_description = "Description"
    bl_options = {"REGISTER"}

    action_group_index: bpy.props.IntProperty()
    action_assigment_index: bpy.props.IntProperty()

    def execute(self, context):
        properties = context.window_manager.action_organizer
        action_group = properties.action_groups[self.action_group_index]
        action_group.action_assignments.remove(self.action_assigment_index)
        return {"FINISHED"}
    
class SelectActionInGroupOperator(bpy.types.Operator):
    bl_idname = "action_organizer.select_action_in_group"
    bl_label = "Select action"
    bl_description = "Description"
    bl_options = {"REGISTER"}

    action_group_index: bpy.props.IntProperty()
    action_assigment_index: bpy.props.IntProperty()

    def execute(self, context):
        properties = context.window_manager.action_organizer
        action_group = properties.action_groups[self.action_group_index]
        action_assignment = action_group.action_assignments[self.action_assigment_index]

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

class ActionOrganizerOperator(bpy.types.Operator):
    bl_idname = "action_organizer.action_organizer"
    bl_label = "Action organizer"
    bl_description = "Description"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(self, context):
        return len(bpy.data.actions) > 0

    def execute(self, context):
        properties = context.window_manager.action_organizer
        return {"FINISHED"}
    
    def invoke(self, context, event):
        properties = context.window_manager.action_organizer
        return context.window_manager.invoke_popup(self)
    
    def draw(self, context):
        properties = context.window_manager.action_organizer

        layout = self.layout
        layout.ui_units_x = 25

        groups_data_column = layout.column()

        for action_group_index, action_group in enumerate(properties.action_groups):
            group_parent = groups_data_column.box()

            # Group label.
            group_label_row = group_parent.row()
            toggle_expanded_operator = group_label_row.operator(
                ToggleActionGroupExpandedOperator.bl_idname,
                text="",
                icon="DOWNARROW_HLT" if action_group.is_expanded else "RIGHTARROW",
                emboss=False
            )
            toggle_expanded_operator.action_group_index = action_group_index
            group_label_row.prop(data=action_group, property="name", text="")

            # Button to remove action group.
            remove_group_operator = group_label_row.operator(RemoveActionGroupOperator.bl_idname, text="", icon="REMOVE")
            remove_group_operator.action_group_index = action_group_index

            if action_group.is_expanded:
                actions_box = group_parent.box()
                
                for action_assignment_index, action_assignment in enumerate(action_group.action_assignments):
                    action_data_row = actions_box.row()

                    # Button to select action and its assigned object.
                    select_action_operator = action_data_row.operator(SelectActionInGroupOperator.bl_idname, text="Select")
                    select_action_operator.action_group_index = action_group_index
                    select_action_operator.action_assigment_index = action_assignment_index

                    # Selection boxes for action and rig object.
                    action_data_row.prop_search(action_assignment, "action", bpy.data, "actions", text="")
                    action_data_row.prop_search(action_assignment, "assigned_rig_object", context.scene, "objects", text="")

                    # Button to remove action assigment.
                    remove_action_operator = action_data_row.operator(RemoveActionAssignmentOperator.bl_idname, text="", icon="REMOVE")
                    remove_action_operator.action_group_index = action_group_index
                    remove_action_operator.action_assigment_index = action_assignment_index

                # Button to create action assigment.
                create_action_row = actions_box.row()
                assignment_operator = create_action_row.operator(CreateActionAssignmentOperator.bl_idname, icon="ADD")
                assignment_operator.action_group_index = action_group_index
        
        # Button to create action group.
        create_group_row = layout.row()
        create_group_row.operator(CreateActionGroupOperator.bl_idname, icon="ADD")

#
# Registration.
#

def menu_func(self, context):
    self.layout.operator(ActionOrganizerOperator.bl_idname, text=ActionOrganizerOperator.bl_label)

classes = (
    ActionAssignmentProperty,
    ActionGroupProperty,
    ActionOrganizerProperties,
    CreateActionGroupOperator,
    RemoveActionGroupOperator,
    ToggleActionGroupExpandedOperator,
    CreateActionAssignmentOperator,
    RemoveActionAssignmentOperator,
    SelectActionInGroupOperator,
    ActionOrganizerOperator,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.WindowManager.action_organizer = bpy.props.PointerProperty(type=ActionOrganizerProperties)
    bpy.types.DOPESHEET_HT_header.append(menu_func)

def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
    del bpy.types.WindowManager.action_organizer
    bpy.types.DOPESHEET_HT_header.remove(menu_func)
