
import json
import shutil
from typing import Type, Any
import inspect
import orjson
import sys
import os

# from primitives.configuration import Configuration
# from primitives.parameter import Parameter
# from utils import interpolate_griddata
sys.path.append(os.path.join(os.path.dirname(__file__),'..'))

from core.Apparatus import *
from core.Executor import *
from core.Procedure import *
from core.boundary.boundary import *
from core.boundary.circle_boundary import *
from core.boundary.ellipse_boundary import *
from core.boundary.rectangle_boundary import *
from core.boundary.triangle_boundary import *
from core.devices.device import *
from core.fileparsers.fileparser import *
from core.fileparsers.g_code_parser import *
from core.gcode.block_gcode_writer import *
from core.gcode.gcode_writer import *
from core.gcode.line_comment import *
from core.gcode.line_gcode_writer import *
from core.gcode.scan_gcode_writer import *
from core.gcode.section_gcode_writer import *
from core.generators.mandrel_scan_generator import *
from core.generators.toolpath_generator import *
from core.layers.layer import *
from core.machine.fiveaxis_machine import *
from core.machine.machine import *
from core.machine.threeaxis_machine import *
from core.machine.axes.axis import *
from core.machine.axes.dispenser_axis import *
from core.machine.axes.endeffector_axis import *
from core.machine.axes.linear_axis import *
from core.machine.axes.mixer_axis import *
from core.machine.axes.rotational_axis import *
from core.materials.cartridge import *
from core.materials.material import *
from core.materials.retractions import *
from core.materials.syringe import *
from core.modifiers.bivariate_compliance_modifier import *
from core.modifiers.bivariate_modifier import *
from core.modifiers.modifier import *
from core.modifiers.univariate_compliance_modifier import *
from core.modifiers.univariate_modifier import *
from core.motion.alternate_motion import *
from core.motion.constant_az_motion import *
from core.motion.elevation_smoothing_motion import *
from core.motion.motion import *
from core.motion.speeds_feeds import *
from core.motion.transitions.leadin_transition import *
from core.motion.transitions.leadout_transition import *
from core.motion.transitions.purge_transition import *
from core.motion.transitions.transition import *
from core.motion.transitions.transition_position import *
from core.part.part import *
from core.setups.mandrel_setup import *
from core.setups.plate_setup import *
from core.setups.setup import *
from core.setups.corrections.corrections import *
from core.setups.corrections.mandrel_corrections import *
from core.setups.corrections.plate_corrections import *
from core.setups.offsets.mandrel_offsets import *
from core.setups.offsets.offsets import *
from core.setups.registration.mandrel_registration import *
from core.setups.registration.plate_registration import *
from core.setups.registration.registration import *
from core.structure.structure import *
from core.structure.conformal.conformal_structure import *
from core.structure.conformal.hatch_structure import *
from core.structure.conformal.hexagon_structure import *
from core.structure.conformal.ring_structure import *
from core.structure.conformal.spiral_structure import *
from core.structure.explicit.explicit import *
from core.structure.explicit.explicit3D_structure import *
from core.substrate.mandrel import *
from core.substrate.plate import *
from core.substrate.substrate import *
from core.toolpath.toolpath import *
from geometry.coordinates import *
from geometry.shape_utils import *
from geometry.strand import *
from primitives.array2D import *
from primitives.configuration import *
from primitives.control import *
from primitives.data import *
from primitives.dependency import *
from primitives.dynamic import *
from primitives.file import *
from primitives.folder import *
from primitives.mod_map import *
from primitives.parameter import *
from primitives.primitive import *
from primitives.struct import *
from utils.class_inspect import *
from utils.decorators import *
from utils.interpolate_griddata import *
from utils.parse_data_A3200 import *
from utils.read_dxf import *
from utils.resource_path import *
from utils.uuid_utils import *
from utils.class_inspect import get_subclasses

CONSTANTS = ['dbName','dbVersion']
FILE_EXTENSION = '.fmwk'

def str_to_class(class_name: str) -> Type:
    try:
        cls = getattr(sys.modules[__name__], class_name)
    except AttributeError:
        raise NameError(f'Class "{class_name}" does not exist.')
    if isinstance(cls, type):
        return cls
    raise TypeError(f'"{class_name}" is not a class')
    
def get_all_children_names(parent:str | Type[Any], as_JSON:bool=True)-> list[str] | str:
    if isinstance(parent,str): parent = str_to_class(parent)
    names = [s.name for s in get_subclasses(parent) if not inspect.isabstract(s)]
    if as_JSON: names = orjson.dumps(names).decode().encode('utf-8')
    return names

def get_all_children_classnames(parent:str | Type[Any], as_JSON:bool=True)-> list[str] | str:
    if isinstance(parent,str): 
        parent_key = parent
        parent = str_to_class(parent)
    else:
        parent_key = parent.__name__
    names = [c.__name__ for c in get_subclasses(parent) if not inspect.isabstract(c)]
    if not inspect.isabstract(parent):
        names.insert(0,parent_key)
    if as_JSON: names = orjson.dumps(names).decode().encode('utf-8')
    return names

def get_all_children_descriptions(parent: str | Type[Any], as_JSON:bool=True) -> dict | str:
    if isinstance(parent,str): 
        parent_key = parent
        parent = str_to_class(parent)
    else:
        parent_key = parent.__name__
    
    descriptions: list[dict] = [{'classname': c.__name__, 'name':c.name, 'description':c.description} 
                                for c in get_subclasses(parent) if not inspect.isabstract(c) and not hasattr(c, 'ISOLATE')] 
    
    if not inspect.isabstract(parent):
        descriptions.insert(0,{'classname':parent.__name__, 'name':parent.name, 'description':parent.description})
    
    descriptions: dict = {parent_key:descriptions}
    if as_JSON: descriptions: str = orjson.dumps(descriptions).decode().encode('utf-8')
    return descriptions

def get_child_description(parent: str | Type[Any], child_name:str, as_JSON:bool=True)->dict | str:
    if isinstance(parent,str): parent = str_to_class(parent)
    description:list[str] = [c.description for c in get_subclasses(cls=parent, match=child_name) if not inspect.isabstract(c)]
    description:dict = {child_name:description}
    if as_JSON: description:str = orjson.dumps(description).decode().encode('utf-8')
    return description

def get_description(cls: str | Type[Configuration] | Type[Parameter], as_JSON:bool = True) -> str:
    if isinstance(cls,str): cls = str_to_class(cls)
    description:str = cls.description
    if as_JSON: description = orjson.dumps(description).decode().encode('utf-8')
    return description

def get_all_children_requirements(parent, as_JSON:bool = True) -> dict[str,Any] :
    if isinstance(parent,str):
        parent = str_to_class(parent)
    else:
        parent_key = parent.__name__
    names = get_all_children_classnames(parent,as_JSON=False)
    requirements = [c().requirements for c in get_subclasses(parent) if not inspect.isabstract(c)]

    requirements = dict(zip(names,requirements))
    requirements = {parent_key: requirements}
    if as_JSON: requirements = orjson.dumps(requirements, option=orjson.OPT_SERIALIZE_NUMPY).decode().encode('utf-8')
    return requirements

def get_child_requirements(parent, child_name, as_JSON=True):
    if isinstance(parent,str): parent = str_to_class(parent)
    requirements = [c().requirements for c in get_subclasses(parent,child_name) if not inspect.isabstract(c)]
    requirements = {child_name:requirements}
    if as_JSON: requirements = orjson.dumps(requirements).decode().encode('utf-8')
    return requirements

def get_all_requirements(cls,as_JSON=True):
    if isinstance(cls,str): cls = str_to_class(cls)
    if inspect.isabstract(cls):
        children = get_all_children_classnames(cls.__name__, False)
        requirements = f"'{cls.__name__}' is an abstract class and cannot be directly initialized. Try get_all_children_requirements() searching for requirements of all children: {children}"
    else:
        requirements =  cls().requirements
    requirements = {cls.__name__: requirements}
    if as_JSON: requirements = orjson.dumps(requirements, option=orjson.OPT_SERIALIZE_NUMPY).decode().encode('utf-8')
    return requirements

def get_all_simple_requirements(cls, as_JSON=True):
    if isinstance(cls,str): cls = str_to_class(cls)
    if inspect.isabstract(cls):
        children = get_all_children_classnames(cls.__name__, False)
        requirements = f"'{cls.__name__}' is an abstract class and cannot be directly initialized. Try get_all_children_requirements() searching for requirements of all children: {children}"
    else:
        requirements =  cls().requirements
    requirements = {cls.__name__: requirements}
    if as_JSON: requirements = orjson.dumps(requirements, option=orjson.OPT_SERIALIZE_NUMPY).decode().encode('utf-8')
    return requirements

def get_all_hashes(cls, control_type, digest_only=True, as_JSON=True):
    if isinstance(cls,str): cls=str_to_class(cls)
    # if isinstance(cls, dict): get_class_from_dict(cls)
    hashes = cls.hash(control_type=control_type)
    if digest_only:
        if hashes:
            import json
            import hashlib
            hashes = json.dumps(hashes, indent=4, sort_keys=True).encode('utf-8')
            hash_digest = hashlib.new('sha256')
            hash_digest.update(hashes)
            hashes=hash_digest.hexdigest()
        else:
            hashes=''

    hashes = {'hash':hashes}
    if as_JSON: hashes = orjson.dumps(hashes, option=orjson.OPT_SERIALIZE_NUMPY).decode().encode('utf-8')
    return hashes
            
def hash_parameter(parameter, as_JSON=True):
    if parameter.__class__.__name__ == 'dict':
        parameter = create_parameter_from_dict(parameter)
    if parameter.__class__.__name__ != 'Parameter':
        raise Exception('The provided data is not a valid Parameter object')
    
    parameter.hash()
    if as_JSON: return parameter.to_json()
    return parameter

def hash_controlled_value(control, value, as_JSON=True):
    import json
    newC = str_to_class('Control')
    newC = newC()
    if control.__class__.__name__ == 'dict':
        newC.__init_from_dict__(control)
        control = newC
        control_hash = control.hash(value)
    elif control.__class__.__name__ == 'Control':
        control_hash = control.hash(value)
    else:   
        try: 
            newC.__init_from_dict__(control)
            control = newC
            control_hash = control.hash(value)
        except:
            raise Exception(f'Provided Input was of type {control.__class__.__name__}. Input must be a dictionary in the form of the Control requirements: {json.dumps(newC.requierments, indent=4,sort_keys=True)}')
        
    control_hash = {'hash':control_hash}
    if as_JSON: control_hash = json.dumps(control_hash,indent=True,sort_keys=True)

def get_child_obj_by_name(parent,child_name):
    if isinstance(parent,str): parent = str_to_class(parent)
    child_list = [c() for c in get_subclasses(parent,child_name)]
    return child_list[0]

def create_parameter_from_dict(parameter_dict, parameter=None):
    if 'classname' not in parameter_dict.keys():
        raise Exception('Provided dictionary does not include the required key "classname"')
    if parameter_dict['classname'] != 'Parameter':
        raise Exception('Provided dictionary is not of type "Parameter". Cannot create class from the provided arguments')
    
    if parameter is None:
        parameter = str_to_class('Parameter')
        parameter = parameter()
    primitives = ['str', 'float', 'int','bool']
    requirements = parameter.requirements
    for key in parameter_dict:
        if key in requirements:
            #DETERMINE the parameter's data type:
            if parameter_dict[key].__class__.__name__ in primitives:
                value_type = 'primitive'
            elif parameter_dict[key].__class__.__name__ == 'list':
                if len(parameter_dict[key]) > 0:
                    if all([v.__class__.__name__ in primitives for v in parameter_dict[key]]):
                        value_type = 'list of primitives'
                    else:
                        #This will also catch mixed in primitives, see below
                        value_type = 'list of objects'
                else:
                    value_type = 'primitive'
            else:
                value_type = 'object'
            
            if value_type == 'primitive' or value_type == 'list of primitives':
                setattr(parameter,key,parameter_dict[key])
            elif value_type == 'object':
                #check if the provided object is a valid framework class
                value = get_class_from_dict(parameter_dict[key])
                setattr(parameter, key, value)
            elif value_type == 'list of objects':
                # For each list item, create the class. Will be either Parameter or Configuration type
                new_list = []
                for object_dict in parameter_dict[key]:
                    #check for primitives mixed in with objects
                    if object_dict.__class__.__name__ in primitives:
                        value = object_dict
                    else:
                        value = get_class_from_dict(object_dict)
                    new_list.append(value)
                setattr(parameter,key, new_list)
    return parameter

def get_class_from_dict(parameter_dict:dict):
    if 'classname' not in parameter_dict.keys():
        raise Exception('ERROR:query.get_class_from_dict -- Provided dictionary does not include the required key "classname"')
    try:
        cls = str_to_class(parameter_dict['classname'])
        cls = cls()
    except:
        raise Exception(f'ERROR:query.get_class_from_dict -- Could not create the class {parameter_dict["classname"]}. Make sure this class exists and is visible to query imports.')
    
    requirements = cls.requirements
    for key in parameter_dict:
        if key in requirements:
            parameter = None
            #Determine if the key is a nested parameter or another framework Configuration class
            if parameter_dict[key].__class__.__name__ == 'dict':
                if 'classname' in parameter_dict[key]:
                    if parameter_dict[key]['classname'] == 'Parameter':
                        #it's a Parameter object
                        default_parameter = getattr(cls,key)
                        if default_parameter.__class__.__name__ == 'Parameter':
                            parameter = create_parameter_from_dict(parameter_dict[key], parameter=default_parameter)
                    else:
                        #it's a framework Configuration class
                        parameter = get_class_from_dict(parameter_dict[key])
                else:
                    raise Exception(f'The key "classname" must be provided at every level of the config tree. No classname key found for object {key}')
            #If neither, then it's a custom class or framework Primitive
            elif parameter_dict[key].__class__.__name__ == 'list':
                new_list = []
                for objDict in parameter_dict[key]:
                    if objDict.__class__.__name__ == 'dict':
                        val = get_class_from_dict(objDict)
                    else:
                        val = objDict
                    new_list.append(val)
                parameter = new_list
            else:
                parameter = parameter_dict[key]

            if parameter is not None: setattr(cls, key, parameter)
            elif key in CONSTANTS:
                parameter = parameter_dict[key]
                parameter = create_parameter_from_dict[parameter_dict[key]]
                if parameter is not None: setattr(cls, key, parameter)
            #CHECK if the dictionary key is a valid class property on dynamic class objects
            elif 'Dynamic' in [base_cls.__name__ for base_cls in type(cls).__bases__]:
                try:
                    if parameter_dict[key].__class__.__name__ == 'dict' and 'classname' in parameter_dict[key]:
                        parameter_dict[key] = get_class_from_dict(parameter_dict[key])

                    #Evaluate property method should throw exception if value is invalid
                    verified_value = cls.evaluate_property(key,parameter_dict[key])
                    parameter_dict[key] = verified_value

                    #Initialize the class key to none, proceed to evaluate further
                    if key not in cls.__dict__.keys():
                        setattr(cls, key, verified_value)
                except:
                    #Ignore invalid properties
                    pass

                    #Alternate implementation - place exceptions here
            else:
                #Handle any other cases here
                # print(f'Generating class {parameter_dict["classname"]}: Ignoring key {key} for Parameter')
                pass

            #UPDATE with dependencies after all parameters have been set
            if 'found_dependencies' in parameter_dict:
                update_with_dependencies(cls, parameter_dict['found_dependencies'],False)

    return cls

def update_with_dependencies(class_dict, dependencies:list, as_JSON=True):
    if class_dict.__class__.__name__ == 'dict':
        #convert parameter dict to object
        cls = get_class_from_dict(parameter_dict=class_dict)
    else:
        cls = class_dict

    #Convert dependency list of dicts to list of objects
    dependency_list = []
    for dependency_dict in dependencies:
        dependency_list.append(get_class_from_dict(dependency_dict))
    
    #GET the parameters that store the dependency reference information
    # --> Alternate check method: Invokes the requirements of the class to verify if p is a valid parameter
    # params = [p for p in class_dict.keys() if class_dict[p].__class__.__name__ == 'dict' and p in cls.requirements.keys() and class_dict[p]['classname']=='Parameter']

    #Faster check method, but potentially less accurate, assumes true Parameter dictionaries have a "classname" field:
    if class_dict.__class.__name__ == 'dict':
        params = [p for p in class_dict.keys() if class_dict[p].__class__.__name__ == 'dict' and 'classname' in class_dict[p] and class_dict[p]['classname']=='Parameter']
        dep_keys = [k for k in params if 'Dependency' in class_dict[k]['allowed_types']]
    else:
        params = [p for p in class_dict.__dict__.keys() if getattr(class_dict,p).__class__.__name__ == 'Parameter']
        dep_keys = [k for k in params if 'Dependency' in getattr(class_dict,k).allowed_types]

    for dep_key in dep_keys:
        dependency_parameter = getattr(cls, dep_key)

        #PROCESS the dependencies with their references
        if hasattr(cls, 'evaluate_dependency') and callable(getattr(cls,'evaluate_dependency')):
            try:
                cls.evaluate_dependency(dependency_list,dependency_parameter)
            except Exception as e:
                print(e)
                pass
        else:
            raise Exception(f'The provided Class {cls.name} must be a valid framework Configuration class with a callable method "evaluate_dependencies()" to perform dependency updates.')
        
    if as_JSON:
        cls = orjson.dumps(cls.requirements,option=orjson.OPT_SERIALIZE_NUMPY).decode()
    return cls


def generate_structure( substrate:dict, structure:dict):
    import numpy as np
    substrate = get_class_from_dict(substrate)
    structure = get_class_from_dict(structure)
    structure.substrate = substrate
    structure.generateCoordinates()
    data = structure.toDict(precision=4)
    #RESHAPE the coords for optimizxed rendering in UI (UI uses Y axis as Vertical for rendering)
    xyz = np.array(data['X'],data['Z'],data['Y']).T
    result = {}
    result['xyz'] = np.ascontiguousarray(xyz)
    result['xyz_flat'] = xyz.flatten()
    result['details'] = structure.getDetails(precision=4)

def generate_toolpath(part:dict,setup:dict, activeSetup:int, output_dir:str):
    part = get_class_from_dict(part)
    setup = get_class_from_dict(setup)
    setup.activeSetup = activeSetup
    toolpath = str_to_class('Toolpath')()
    toolpath_generator = str_to_class('ToolpathGenerator')()
    toolpath.part = part
    toolpath.setup = setup
    toolpath_generator.part = part
    toolpath_generator.setup = setup
    toolpath_generator.output_folder = output_dir
    toolpath_generator.toolpath = toolpath
    result = toolpath_generator.generateAllLayers(output_dir=output_dir, return_precision=3)
    result = orjson.dumps(result, option=orjson.OPT_SERIALIZE_NUMPY).decode()
    return result

def generate_toolpath_2(part,setup,activeSetup:int,output_dir:str, details:dict,startFileTemplates:list, printlabel:bool):
    part_config = get_class_from_dict(part[part['configType']])
    setup_config = get_class_from_dict(setup[setup['configType']])
    setup_config.activeSetup = activeSetup
    sft_configs = []
    for sft in startFileTemplates:
        sft_configs.append(get_class_from_dict(sft[sft['configType']]))
    toolpath = str_to_class('Toolpath')()
    toolpath_generator = str_to_class('ToolpathGenerator')()
    toolpath.part = part_config
    toolpath.setup = setup_config
    toolpath_generator.part = part_config
    toolpath_generator.setup = setup_config
    toolpath_generator.output_dir = output_dir
    toolpath_generator.toolpath = toolpath
    toolpath_generator.startFileTemplates = sft_configs
    toolpath_generator.printLabel = printlabel
    result = toolpath_generator.generateAllLayers(output_dir=output_dir,return_precision=3,details=details,printlabel=printlabel)
    result = orjson.dumps(result, option=orjson.OPT_SERIALIZE_NUMPY).decode()
    return result

def generate_scan(setup:dict, activeSetup:int, output_folder:None):
    setup = get_class_from_dict(setup)
    setup.activeSetup=activeSetup
    scan_preset = str_to_class('Scan_Preset')()
    scan_preset.setup = setup
    scan_path = scan_preset.generate_scan(output_folder=output_folder)
    result = {'scan_path':scan_path,'setup':setup.requirements}
    result = orjson.dumps(result,option=orjson.OPT_SERIALIZE_NUMPY).decode()
    return result

def processScan(setup:dict, activeSetup:int, zipFile:str):
    setup = get_class_from_dict(setup)
    setup.activeSetup = activeSetup
    scan = setup.get_active_scan()
    if scan:
        filepath = scan.processMapScan(zipFile=zipFile)
        return orjson.dumps({'Filepath':filepath})
    
def process_offsets(setup:dict, rotateReadFile:str, activeSetup:int):
    setup = get_class_from_dict(setup)
    setup.activeSetup = activeSetup
    setup.process_offsets(rotateReadFile=rotateReadFile)
    result = {'setup':setup.requirements}
    result = orjson.dumps(result,option=orjson.OPT_SERIALIZE_NUMPY).decode()
    return result

def interpolate_grid(IV1,IV2,DV):
    result = interpolate_griddata(ind_var_1=IV1, ind_var_2=IV2, dep_var=DV)
    result = orjson.dumps(result,option=orjson.OPT_SERIALIZE_NUMPY).decode()
    return result

def calculateScanCorrections(vertices,scanFile):
    import numpy as np
    #create a new mandrel object
    mandrel = str_to_class('Mandrel')()
    #Create a new coordinates object
    coordinates = str_to_class('Coordinates')()
    #Reshape the vertices
    xyz = np.reshape(vertices,(int(len(vertices/3),3))).T
    #incoming vertices has Z column in second column, swap to third column
    xyz[[1,2]] = xyz[[2,1]]
    #convert vertices from cartesian to polar
    [polar,az,_] = coordinates.Cartesian2Spherical(xyz)
    coordinates.X = vertices[0]
    coordinates.Y = vertices[1]
    coordinates.Z = vertices[2]
    coordinates.Polar = polar
    coordinates.Az = az

    scanFile = get_class_from_dict(scanFile)

    corrections = mandrel.calculateScanCorrections(coordinates=coordinates, scanFile=scanFile.local_filepath)

    #serialize to json
    result = orjson.dumps({'corrections':corrections, 'min':corrections.min(),'max':corrections.max()}, options=orjson.OPT_SERIALIZE_NUMPY).decode()
    return result

def save_config(config_dict:dict):
    config_type = config_dict['configType']
    config = config_dict[config_type]
    config = get_class_from_dict(config)
    return config.simple_requirements

def load_config(config_dict:dict):
    config_type = config_dict['configType']
    config = config_dict[config_type]
    config = get_class_from_dict(config)
    return config.requirements

def export_config(dir_path:str,config_dict:dict,downloaded_files:list):
    import shutil
    warnings=''
    status='success'
    def remove_bad_chars(string):
        bad_chars=['\\','/','*','?','"','<','>','|',':']
        for c in bad_chars:
            string = string.replace(c,'_')
        return string
    
    config_type = config_dict['configType']
    config = config_dict[config_type]
    config = get_class_from_dict(config)
    config[config_type] = config.simple_requirements

    export_name = f'{config_type}_{remove_bad_chars(config_dict["name"])}_V{config_dict["version"]}'
    config_filename = f'{export_name}.json'
    output_path = os.path.join(dir_path,export_name)
    if not os.path.isdir(output_path):
        os.mkdir(output_path)

    config_filepath = os.path.join(output_path,config_filename)

    try:
        with open(config_filepath,'wb') as configFile:
            configFile.write(orjson.dumps(config_dict,option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_INDENT_2))
        copied_files = [config_filepath]

        for fil in downloaded_files:
            if fil['local_filepath']:
                filepath = os.path.join('[exported_path]',fil['filename'])
        support_files_filepath = os.path.join(output_path,'support_files.json')
        with open(support_files_filepath,'wb') as support_file:
            support_file.write(orjson.dumps(downloaded_files,option=orjson.OPT_INDENT_2))
            if support_files_filepath not in copied_files: copied_files.append(support_files_filepath)

        shutil.make_archive(output_path,'zip',output_path)
        #overwrite previous export with sane name
        exp_file = f'{output_path}{FILE_EXTENSION}'
        if os.path.isfile(exp_file):
            os.remove(exp_file)
        os.rename(f'{output_path}.zip',exp_file)
        status='success'
    except Exception as e:
        status=f'An error occured, failed to export {export_name}. Error details:\n\n{str(e)}'
    
    try:
        for fil in copied_files:
            os.remove(fil)
        os.rmdir(output_path)
    except Exception:
        warnings = f'{warnings}"Could not remove files/folders from"{output_path}" after zipping data\n"'

    return {'export':status,'warnings':warnings}

def import_config(filepath:str, config_type:str):

    if not os.path.isfile(filepath):
        raise Exception(f'Filepath provided is not a valid file \n\n: {filepath}')
    if not filepath.endswith(FILE_EXTENSION):
        raise Exception(f'Filepath must be a valid {FILE_EXTENSION} file')

    from primitives.file import File
    from primitives.folder import Folder

    directory = filepath.replace(FILE_EXTENSION,'')
    filename = os.path.basename(directory)
    jsonpath = os.path.join(directory,f'{filename}.json')

    os.rename(filepath,filepath.replace(FILE_EXTENSION,'.zip'))
    filepath = filepath.replace(FILE_EXTENSION,'.zip')
    shutil.unpack_archive(filepath, directory,'zip')
    os.rename(filepath, filepath.replace('.zip',FILE_EXTENSION))

    import_data=None
    with open(jsonpath) as configFile:
        try:
            import_data = json.loads(configFile.read())
        except:
            #Pass here and raise exception on import_data = None
            pass
    if import_data is None:
        raise Exception(f'Could not read the file. Make sure it is a valid {FILE_EXTENSION} export file')
    
    required_keys = ['configType','name','version','id_number','classification']
    found_keys = [k for k in import_data.keys() if k in required_keys]
    if len(found_keys) != len(required_keys):
        err_msg = f'The provided {FILE_EXTENSION} file is not a valid {config_type} Configuration.'
        if 'config_type' in found_keys:
            err_msg = f'{err_msg} It is a {import_data["configType"]} configuration'
        raise Exception(err_msg)
    
    support_files = None
    support_filepath = os.path.join(directory, 'support_files.json')
    if not os.path.isfile(support_filepath):
        raise Exception(f'Reference to support_files.json in the {FILE_EXTENSION} export is missing')
    
    with open(support_filepath) as f:
        try:
            support_files = json.loads(f.read())
        except:
            pass
    if support_files is None:
        raise Exception(f'Could not read data from "support_files.json." Make sure the {FILE_EXTENSION} file is a valid export file')
    
    for fil in support_files:
        fil['local_filepath'] = fil['local_filepath'].replace('[exported_path]',directory)
        if fil['local_filepath'] and not os.path.isfile(fil['local_filepath']):
            raise Exception(f'IMPORT ERROR: support_files.json in {filepath} points to a missing reference to {fil["local_filepath"]}')
    dummy_file = File()
    default_download_dir = dummy_file.download_directory
    File.download_directory = directory
    dummy_folder = Folder()

    if config_type not in import_data.keys():
        raise Exception(f'The provided {FILE_EXTENSION} file does not have the correct config type data. Expected key for {config_type} data')
    
    configType = import_data['configType']
    config = get_class_from_dict(import_data[configType])
    import_data[configType] = config.requirements
    File.download_directory = default_download_dir
    if len(dummy_folder.all_warnings) > 0:
        import_data['warnings'] = []
        for warning in dummy_folder.all_warnings:
            if warning not in import_data['warnings']: import_data['warnings'].append(warning)

    return import_data
