from A3200StatusItem import A3200StatusItem
from A3200AxisStatus import A3200AxisStatus
import queue
import threading
import ctypes as ct
import time
import collections
import os

class Axis:
    
    name='Axis'
    description='A simplistic representatin of an Axis object'

    def __init__(self, axis_name:str, driver_index:int) -> None:
        '''
            This is a simplified version of an Axis object.
            axis_name -> name of the axis as defined in the A3200 parameter file, i.e. 'X', 'Y', 'Z', etc
            driver_index -> index of the axis as defined in the A3200 parameter file. Generally coincides with the index of the phyisical connector location on the NPAQ
        '''
        self.axis_name = axis_name
        self.driver_index = driver_index


# Define data types
A3200Handle = ct.c_void_p  # A3200Handle  pointer type
WORD  = ct.c_uint16
DWORD = ct.c_uint32
STATUSITEM = ct.c_uint32  
DOUBLE = ct.c_double

class A3200_NPAQ:
    name ='A3200 Driver (NPAQ)'
    description = 'Control interface with Aerotech A3200 NPAQ drivers'

    def __init__(self, task:int=0, simulation:bool=True, dll_path:str='',default_motion_speed:float=20.0) -> None:
        '''
            'default_task' : 'Default task for A3200 driver',
            'simulation' : 'If true, will not execute commands on physical hardware -- only run in software mode',
            'dll_path' : 'Filepath to the directory containing the A3200 dynamic linked library (DLL) files (.dll)',
            'default_motion_speed': 'The default speed (F-Rate) to move axes during jog, travel, or when speed is not defined'
        '''
        
        self.task = task
        self.simulation = simulation
        self.dll_path = dll_path
        self.default_motion_speed = default_motion_speed

        self.max_tasks = 4 #limitation of A3200 controller driver
        self.A3200_is_open = False
        self.A3200_lib = None

        ##Attempt initial connection
        self.handle , self.A3200_lib = self.connect()
        if self.handle : self.A3200_is_open =True

        self.queue_status = [0]*self.max_tasks
        self.queue_return = None
        self.queue_process = None
        self.queue_poll_time = 0.05 #seconds

    def connect(self):
        '''
            Connect to the A3200 driver and return a handle
        '''
       
        if self.simulation:
            print('Initializing A3200 in simulation mode')
            return None, self.A3200_lib

        if not self.A3200_lib:
            try:
                self.A3200_lib = ct.WinDLL(os.path.join(self.dll_path.path,'A3200.dll'))
            except:
                self.A3200_is_open = False
                raise A3200Exception('A3200:connect', 'Failed to connect', 'estop')
        
        if not self.A3200_is_open:
            handle = ct.c_void_p()
            if self.A3200_lib.A3200Connect(ct.byref(handle)):
                print("successfully connected to A3200")
                self.A3200_is_open = True
                return handle, self.A3200_lib
            else:
                self.A3200_is_open = False
                raise A3200Exception('A3200:connect', 'Failed to connect', 'estop')
        
    def disconnect(self):
        if self.A3200_is_open and self.A3200_lib is not None:
            return self.A3200_lib.A3200Disconnect(self.handle)
        
    def enable(self, axes: 'list[Axis]', task: int | None=None):
        '''
            Enables the axes on the provided task id
        '''
        if self.A3200_is_open:
            ax_mask = self.get_axis_mask(axes=axes)
            task = task if task is not None else self.task
            return self.A3200_lib.A3200MotionEnable(self.handle, task, ax_mask)
        
    def disable(self, axes:'list[Axis]', task: int | None=None):
        '''
            Disable the specified axes on the provided task id
        '''
        if self.A3200_is_open:
            ax_mask = self.get_axis_mask(axes=axes)
            task = task if task is not None else self.task
            return self.A3200_lib.A3200MotionDisable(self.handle, task, ax_mask)

    def acknowledge_fault(self, axes:'list[Axis]', task:int|None=None):
        '''
            Acknowledge axis fault on the specified axes
        '''
        if self.A3200_is_open:
            ax_mask = self.get_axis_mask(axes=axes)
            task = task if task is not None else self.task
            return self.A3200_lib.A3200MotionFaultAck(self.handle, task, ax_mask)

    def acknowledge_all(self, task:int|None=None):
        '''
            Acknowledge axis fault on the specified axes
        '''
        if self.A3200_is_open:
            task = task if task is not None else self.task
            return self.A3200_lib.A3200AcknowledgeAll(self.handle, task)

    def abort(self, axes:'list[Axis]',task:int | None=None):
        '''
            Aborts motion on specified axes. Returns when abort signal starts
        '''
        if self.A3200_is_open:
            ax_mask = self.get_axis_mask(axes=axes)
            return self.A3200_lib.A3200MotionAbort(self.handle, ax_mask)

    def auto_focus(self, axis:'Axis', on_off:bool, task:int|None=None):
        '''
           Sets autofocus on or off -- 
           NOTE: AutoFocus parameters need to be set for behavior
           TODO: Implement autofocus parameter setting via this api
        '''
        if self.A3200_is_open:
            task = task if task is not None else self.task
            on_off = ct.c_bool(on_off)
            return self.A3200_lib.A3200MotionAutoFocus(self.handle, task, axis.driver_index, on_off)

    def home(self, axes:'list[Axis]', task:int|None=None):
        '''
           Homes the specified axes
        '''
        if self.A3200_is_open:
            ax_mask = self.get_axis_mask(axes=axes)
            task = task if task is not None else self.task
            return self.A3200_lib.A3200MotionHome(self.handle, task, ax_mask)
    
    def linear(self, axes:'list[Axis]', distances:list[float], task:int | None=None):
        '''
            Make a (G1) linear coordinated point-to-point motion on axes by a specified distance
            using the modal feed rate 
            NOTE: Fails if more than four axes specified and ITAR controls enabled on hardware
        '''
        if self.A3200_is_open:
            speeds = [self.default_motion_speed]*len(axes)
            
            sorted_axes, sorted_distances, _ = self.sort_axes(axes=axes, distances=distances, speeds=speeds)
            #Convert python floats to c doubles
            d = (ct.c_double * len(sorted_distances))(*sorted_distances)

            ax_mask = self.get_axis_mask(axes=sorted_axes)
            task = task if task is not None else self.task
            success = self.A3200_lib.A3200MotionLinear(self.handle, task, ax_mask,d)
            if not success: 
                raise A3200Exception(source='A3200:linear',message=f'A3200 command fail {success}', level='estop')

    def linear_velocity(self, axes:'list[Axis]', distances:list[float], speed: float | None=None, task:int | None=None):
        '''
            Make a (G1) linear coordinated point-to-point motion on axes by a specified distance
            at the specified coordinated speed (F-Rate)
            NOTE: Fails if more than four axes specified and ITAR controls enabled on hardware
        '''
        if self.A3200_is_open:
            speeds = [0.0]*len(axes) 
            
            sorted_axes, sorted_distances, _ = self.sort_axes(axes=axes, distances=distances, speeds=speeds)
            #Convert python floats to c doubles
            d = (ct.c_double * len(sorted_distances))(*sorted_distances)
            F = DOUBLE(speed)

            ax_mask = self.get_axis_mask(axes=sorted_axes)
            task = task if task is not None else self.task
            success = self.A3200_lib.A3200MotionLinearVelocity(self.handle, ax_mask,d,F)
            if not success: 
                raise A3200Exception(source='A3200:linear_velocity',message=f'A3200 command fail {success}', level='estop')
                
    def freerun(self, axis:'Axis',speed:float,task:int | None= None):
        if self.A3200_is_open:
            task = task if task is not None else self.task
            s = ct.c_double(speed)
            return self.A3200_lib.A3200MotionFreeRun(self.handle, task, axis.driver_index, s)
        
    def freerun_stop(self, axis:'Axis', task:int|None=None):
        if self.A3200_is_open:
            task = task if task is not None else self.task
            return self.A3200_lib.A3200FreeRunStop(self.handle,task,axis.driver_index)
        
    def absolute_move(self, axis:'Axis', position:float, speed: float | None=None, task:int | None=None):
        '''
            Make a move on axis to an absolute position
        '''
        if self.A3200_is_open:
            if speed is None: speed = self.default_motion_speed
            #Convert python floats to c doubles
            p = ct.c_double*position
            s = ct.c_double*speed
            task = task if task is not None else self.task
            success = self.A3200_lib.A3200MotionMoveAbs(self.handle, axis.driver_index,p,s)
            if not success: 
                raise A3200Exception(source='A3200:linear',message=f'A3200 command fail {success}', level='estop')

    def incremental_move(self, axis:'Axis', position:float, speed: float | None=None, task:int | None=None):
        '''
            Execute an incremental move on specified axis
        '''
        if self.A3200_is_open:
            if speed is None: speed = self.default_motion_speed
            #Convert python floats to c doubles
            p = ct.c_double*position
            s = ct.c_double*speed
            task = task if task is not None else self.task
            success = self.A3200_lib.A3200MotionMoveInc(self.handle, axis.driver_index,p,s)
            if not success: 
                raise A3200Exception(source='A3200:linear',message=f'A3200 command fail {success}', level='estop')

    def rapid(self, axes:'list[Axis]', distances:list[float], speeds: list[float] | None=None, task:int | None=None):
        '''
            Make a single or multi-axis coordinated point-to-point motion on axes by a specified distance
            NOTE: Fails if more than four axes specified and ITAR controls enabled on hardware
        '''
        if self.A3200_is_open:
            if speeds is None: speeds = [self.default_motion_speed]*len(axes)
            
            sorted_axes, sorted_distances, sorted_speeds = self.sort_axes(axes=axes, distances=distances, speeds=speeds)
            #Convert python floats to c doubles
            d = (ct.c_double * len(sorted_distances))(*sorted_distances)
            s = (ct.c_double * len(sorted_speeds))(*sorted_speeds)

            ax_mask = self.get_axis_mask(axes=sorted_axes)
            success = self.A3200_lib.A3200MotionRapid(self.handle, ax_mask,d ,s)
            if not success: 
                raise A3200Exception(source='A3200:rapid',message=f'A3200 command fail {success}', level='estop')
            
    def wait_for_move_done(self, axes:'list[Axis]', mode:str='move_done', timeout:int =-1):
        '''
            Waits for motion to be done on specified axes. Command will block until motion is done
            on given axes with given criteria, or the wait times out
            mode: 'move_done' | 'in_position'
            timeout: in milliseconds (-1 wait forever, 0 no wait)
            returns timed_out
        '''
        if self.A3200_is_open:
            
            ax_mask = self.get_axis_mask(axes=axes)
            wait_mode = ct.c_ulong(1) if mode == 'in_position' else ct.c_ulong(0)
            timeout = ct.c_int(timeout)
            ret_timeout = ct.c_bool(False)
            success = self.A3200_lib.A3200MotionWaitForMotionDone(self.handle, ax_mask,wait_mode, timeout, ret_timeout)
            return success, ret_timeout

    def cmd_exe(self, command, task: int | None):
        '''
            Execute an Aerobasic command
            command: a string containing the command as written in Aerobasic literal
        '''
        if self.A3200_is_open:
            cmd = ct.c_buffer(command.encode('utf-8'))
            task = task if task is not None else self.task
            success = self.A3200_lib.A3200CommandExecute(self.handle, task, cmd, None)
            return bool(success), str(cmd)

    def program_add(self,filepath:str):
        if self.A3200_is_open:
            program = ct.c_char_p(filepath.encode('utf-8'))
            return self.A3200_lib.A3200ProgramAdd(self.handle, program)

    def program_associate(self,filepath:str,task:int|None=None):
        if self.A3200_is_open:
            program = ct.c_char_p(filepath.encode('utf-8'))
            task = task if task is not None else self.task
            return self.A3200_lib.A3200ProgramAssociate(self.handle, task, program)
        
    def program_load(self,filepath:str,task:int|None=None):
        if self.A3200_is_open:
            program = ct.c_char_p(filepath.encode('utf-8'))
            task = task if task is not None else self.task
            return self.A3200_lib.A3200ProgramLoad(self.handle, task, program)
 
    def program_pause(self,task:int|None=None):
        if self.A3200_is_open:
            task = task if task is not None else self.task
            return self.A3200_lib.A3200ProgramPause(self.handle, task)
        
    def program_pause_and_wait(self,task:int|None=None, timeout:int=-1):
        '''
            timeout in milliseconds: -1 no timeout, 0 timeout immediately
        '''
        if self.A3200_is_open:
            task = task if task is not None else self.task
            timeout = ct.c_int(timeout)
            return self.A3200_lib.A3200ProgramPauseAndWait(self.handle, task, timeout)
        
    def program_remove(self,program_name:str):
        '''
            Removes an Aerobasic program from the SMC. The specified Aerobasic file will
            be completely removed from the SMC. The program should not be associated with any tasks
        '''
        if self.A3200_is_open:
            program = ct.c_char_p(program_name.encode('utf-8'))
            task = task if task is not None else self.task
            return self.A3200_lib.A3200ProgramRun(self.handle, program)
        
    def program_retrace(self,on_off:bool, task:int|None=None):
        if self.A3200_is_open:
            task = task if task is not None else self.task
            on_off = ct.c_bool(on_off)
            return self.A3200_lib.A3200ProgramRetrace(self.handle, task, on_off)
    
    def program_set_line_number(self, line_number:int, task:int|None=None):
        if self.A3200_is_open:
            task = task if task is not None else self.task
            line_number = ct.c_uint32(line_number)
            return self.A3200_lib.A3200ProgramSetLineNumber(self.handle, task, line_number)

    def program_start(self, task:int|None=None):
        if self.A3200_is_open:
            task = task if task is not None else self.task
            return self.A3200_lib.A3200ProgramStart(self.handle, task)

    def program_step_into(self, task:int|None=None):
        if self.A3200_is_open:
            task = task if task is not None else self.task
            return self.A3200_lib.A3200ProgramStepInto(self.handle, task)
 
    def program_step_over(self, task:int|None=None):
        if self.A3200_is_open:
            task = task if task is not None else self.task
            return self.A3200_lib.A3200ProgramStepOver(self.handle, task)
 
    def program_run(self,filepath:str,task:int|None=None):
        if self.A3200_is_open:
            program = ct.c_char_p(filepath.encode('utf-8'))
            task = task if task is not None else self.task
            return self.A3200_lib.A3200ProgramRun(self.handle, task, program)
            
    def program_buffered_run(self,filepath:str, task:int|None=None):
        if self.A3200_is_open: 
            program = ct.c_char_p(filepath.encode('utf-8'))
            task = task if task is not None else self.task
            return self.A3200_lib.A3200ProgramBufferedRun(self.handle, task, program)
        
    def program_stop(self, task:int|None=None):
        if self.A3200_is_open:
            task = task if task is not None else self.task
            return self.A3200_lib.A3200ProgramStop(self.handle, task)

    def program_stop_and_wait(self,task:int|None=None, timeout:int=-1):
        if self.A3200_is_open:
            task = task if task is not None else self.task
            timeout = ct.c_int(timeout)
            return self.A3200_lib.A3200ProgramStopAndWait(self.handle, task, timeout)

    def sort_axes(self, axes: 'list[Axis]', distances: list[float], speeds:list[float]) -> 'tuple[list[Axis], list[float], list[float]]':
        # Pair each Axis object with its corresponding distance
        grouped = list(zip(axes, distances,speeds))

        # Sort the pairs based on the index of the Axis object
        grouped.sort(key=lambda x: x[0].driver_index)

        # Unzip the pairs back into two separate lists
        sorted_axes, sorted_distances, sorted_speeds = zip(*grouped)

        return list(sorted_axes), list(sorted_distances), list(sorted_speeds)

    def get_axis_mask(self,axes: 'list[Axis]'):
        '''
            returns the sum of axes masks for a given list of axis
        '''
        # check if axes is iterable and not a string
        if isinstance(axes, collections.Iterable) and type(axes) is not str:
            mask = 0
            for ax in axes:
                try:
                    mask += (1 << ax.driver_index)
                except Exception:
                    print(f'Invalid axis driver index on axis {ax.axis_name}')
        else:
            raise TypeError(f'A3200:get_axis_mask - axes property must be list of Axis objects')

# '''
#     I/O Commands
# '''
    def analog_input(self,axis:'Axis', channel:int, task:int|None=None):
        if self.A3200_is_open:
            task = task if task is not None else self.task
            ax = ct.c_int(axis.driver_index)
            ch = ct.c_uint(channel)
            ai_return = ct.c_double(0.0)
            success = self.A3200_lib.A3200IOAnalogInput(self.handle,task,ch,ax,ct.byref(ai_return))
            if not success:
                raise A3200Exception('A3200:analog_input', 'Analog Input function failed', 'e-stop')
            return ai_return

    def analog_output(self,axis:'Axis', channel:int, value:float, task:int|None=None):
        if self.A3200_is_open:
            task = task if task is not None else self.task
            ax = ct.c_int(axis.driver_index)
            ch = ct.c_uint(channel)
            val = ct.c_double(value)
            success = self.A3200_lib.A3200IOAnalogOutput(self.handle,task, ch,ax,val)
            if not success:
                raise A3200Exception('A3200:analog_input', 'Analog Input function failed', 'e-stop')
            return success

    def digital_input(self,axis:'Axis', word:int, task:int|None=None):
        if self.A3200_is_open:
            task = task if task is not None else self.task
            ax = ct.c_int(axis.driver_index)
            w = ct.c_uint16(word)
            di_return = ct.c_uint(0)
            success = self.A3200_lib.A3200IODigitalInput(self.handle,task, w,ax,ct.byref(di_return))
            if not success:
                raise A3200Exception('A3200:digital_input', 'Digital Input function failed', 'e-stop')
            return di_return
        
    def digital_output(self,axis:'Axis', word:int, value:int, task:int|None=None):
        if self.A3200_is_open:
            task = task if task is not None else self.task
            ax = ct.c_int(axis.driver_index)
            w = ct.c_uint16(word)
            val = ct.c_uint32(value)
            success = self.A3200_lib.A3200IODigitalOutput(self.handle,task, w,ax,val)
            if not success:
                raise A3200Exception('A3200:digital_output', 'Digital Output function failed', 'e-stop')
            return success
# '''
#     Status Commands
# '''
    def enable_queue_mode(self,task:int | None = None) -> bool | None:
        if self.A3200_is_open:
            task = task if task is not None else self.task
            if self.queue_status[task] == 0:
                if self.A3200_lib.A3200ProgramInitializeQueue(self.handle,task):
                    self.queue_status[task] = 1
                    self.queue_return = queue.Queue()
                    self.queue_process = threading.Thread(
                        target=self.queue_monitor,
                        args=(task)
                    )
    def disable_queue_mode(self, task:int|None=None, wait_until_empty:bool=True) -> bool | None:
        if self.A3200_is_open:
            task = task if task is not None else self.task
            if self.queue_status[task] > 0:
                time.sleep(self.queue_poll_time)
                self.set_task_variables(50,[0])

                if wait_until_empty:
                    while self.get_queue_depth() > 1:
                        time.sleep(self.queue_poll_time)
                self.queue_status[task] = 0
                time.sleep(self.queue_poll_time)
                self.queue_process.join()
                return bool(self.A3200_lib.A3200ProgramStop(self.handle.task))
            
    def queue_monitor(self, task: int):
        if self.A3200_is_open:
            task = task if task is not None else self.task
            bf = 100
            empty = ' '*bf
            error_string = ct.c_buffer(empty.encode('utf-8'))
            buffer_size = ct.c_int(bf)
            while self.queue_status[task] != 0:
                depth = self.get_queue_depth[task]
                time.sleep(self.queue_poll_time)
                if depth < 2:
                    success = self.cmd_exe(f'WAIT(TASKSTATUS({int(task)}, DATAITEM_QueueLineCount)>1) 10000')
                    self.A3200_lib.A3200GetLastErrorString(error_string,buffer_size)
                    self.queue_return.put(f'{success}, {error_string}')
            self.queue_status[task] = 0

    def get_queue_depth(self,task:int|None=None) -> int | None:
        if self.queue_status[task] > 0:
            return None #Task is not in queue mode
        if self.simulation:
            return 0 #TODO: determine a better default depth for simulation mode
        if self.A3200_is_open:
            task = task if task is not None else self.task
            item_code = A3200StatusItem.StatusItem_QueueLineCount
            queue_depth = self.get_status_item(item_code=item_code, item_index=task)
            if queue_depth: queue_depth = int(queue_depth)
            return queue_depth          

    def get_queue_capacity(self,task:int|None=None) -> int | None:
        if self.queue_status[task] > 0:
            return None #Task is not in queue mode
        if self.simulation:
            return 400 #TODO: determine a better default capacity for simulation mode
        if self.A3200_is_open:
            task = task if task is not None else self.task
            item_code = A3200StatusItem.StatusItem_QueueCapacity
            queue_capacity = self.get_status_item(item_code=item_code, item_index=task)
            if queue_capacity: queue_capacity = int(queue_capacity)
            return queue_capacity          

    def get_status_item(self, item_code: A3200StatusItem | A3200AxisStatus, item_index:int, extra: int | None=None) -> float | None:
        '''
            Retrieves a single status item from the A3200. 

            This function will retrieve the specified status item. Provide the item code to collect, corresponding axis or task, and optional extra data. This function works similarly to the AXISSTATUS, TASKSTATUS, and SYSTEMSTATUS AeroBasic functions.

            Parameters:
            [in]  handle  The handle to the A3200  
            [in]  itemIndex  An index to specify which axis, task, or channel index this status item is retrieved from.  
            [in]  itemCode  The item code to retrieve.  
            [in]  itemExtra  Additional data that may be required by some item codes.  
            
        '''
        
        if self.simulation or not self.A3200_is_open:
            return None
        
        if self.queue_status[item_index] > 0:
            item_value = ct.c_double()
            item_index = ct.c_int32(item_index)
            item_code = ct.c_int32(item_code) 
            if extra is None:
                extra = ct.c_int32(0)
            elif isinstance(extra, int) and extra > 0:
                extra = ct.c_int(extra)
            else:
                raise Exception(f'A3200:get_status_item - argument "extra" must be an unsigned integer (positive integer)')

            self.A3200_lib.A3200StatusGetItem(self.handle, item_index, item_code, extra, ct.byref(item_value))
            return float(item_value)
        
    def get_status_items(self, item_indices: list[int], item_codes: list[A3200StatusItem], item_extras: list[int] | None) -> list[float] | None:
        '''
        Retrieves multiple status items from the A3200. 

        This function will retrieve an array of status items. 
        Provide the item codes to collect, corresponding axes or tasks, 
            and optional extra data. 
            
        This function works similarly to the AXISSTATUS, TASKSTATUS, and SYSTEMSTATUS AeroBasic functions.
        
        #### C USAGE EXAMPLE:
        ```C
        A3200Handle handle = NULL;
        if(A3200Connect(&handle)) {
                // we want information for axis #0 and Task #1
                WORD itemAxisTaskIndexArray[] = { AXISINDEX_00, AXISINDEX_00, TASKID_01 };

                // we want position command, position feedback, and task mode
                STATUSITEM itemCodeArray[] = { STATUSITEM_PositionCommand, STATUSITEM_PositionFeedback, STATUSITEM_TaskMode };

                // extra items usually do not matter, but for some items they do; we want only a few bits of task mode
                DWORD itemExtrasArray[] = { 0, 0, TASKMODE_Absolute|TASKMODE_Minutes|TASKMODE_Secondary };
                DOUBLE itemValuesArray[3];

                // get all 3 items together
                A3200StatusGetItems(handle, 3, itemAxisTaskIndexArray, itemCodeArray, itemExtrasArray, itemValuesArray);
                A3200Disconnect(handle);
        }       
        ```
        '''
        if self.simulation or not self.A3200_is_open:
            return None
        
        if item_extras is None:
            item_extras = [0]*len(item_indices)

        if len(item_indices) != len(item_codes) != len(item_extras):
            raise Exception(f'A3200:get_status_items - item_indices, item_codes, and item_extras (optional) must be same length')
        #convert python types to c types
        num_items = len(item_indices)
        item_values = [0.0]*num_items
        ItemIndexArrayType = ct.c_uint16 * num_items
        ItemCodeArrayType = WORD * num_items
        ItemExtrasArrayType = DWORD * num_items
        ItemValuesArrayType = DOUBLE * num_items

        c_numberOfItems = DWORD(num_items)
        c_itemIndexArray = ItemIndexArrayType(*item_indices)
        c_itemCodeArray = ItemCodeArrayType(*item_codes)
        c_itemExtrasArray = ItemExtrasArrayType(*item_extras)
        c_itemValuesArray = ItemValuesArrayType(*item_values)

        success = self.A3200_lib.A3200StatusGetItems(self.handle,c_numberOfItems, c_itemIndexArray, c_itemCodeArray, ct.byref(c_itemExtrasArray), ct.byref(c_itemValuesArray))
        if success:
            # Convert the ctypes array to a Python list of floats
            return [float(value) for value in c_itemValuesArray]
        else:
            raise Exception(f'A3200:get_status_items - An error occured when trying to get status items')
    
    def get_positions(self, axes:'list[Axis]') -> list[float] | None:
        if self.A3200_is_open and not self.simulation:
            num_items = len(axes)
            item_indices = [ax.driver_index for ax in axes]
            item_codes = [A3200StatusItem.STATUSITEM_PositionFeedback]*num_items
            positions = self.get_status_items(item_indices=item_indices, item_codes=item_codes)
            return positions
        
    def get_position(self,axis:'Axis')->float:
        if self.A3200_is_open and not self.simulation:
            positions = self.get_status_item(item_code=A3200StatusItem.STATUSITEM_PositionFeedback,item_index=axis.driver_index)
            return positions

    def is_move_done(self,axis:'Axis',mode:str='done') -> float | None:
        if self.A3200_is_open and not self.simulation:
            move_done = self.get_status_item(item_code=A3200AxisStatus.AXISSTATUS_MoveDone, item_index=axis.driver_index)
            return move_done

    def set_absolute(self,task:int|None=None)->bool:
        if self.A3200_is_open and not self.simulation:
            task = task if task is None else self.task
            success = self.A3200_lib.A3200MotionSetupAbsolute(self.handle, task)
            return success
    
    def set_incremental(self,task:int|None=None) -> bool:
        if self.A3200_is_open and not self.simulation:
            task = task if task is None else self.task
            success = self.A3200_lib.A3200MotionSetupIncremental(self.handle, task)
            return success

    def setup(self):
        '''
            Some functions require arg and return types to be set
        '''
        self.A3200_lib.A3200MotionLinear.argtypes = [
            ct.c_void_p,
            ct.c_uint,
            ct.c_ulong,
            ct.POINTER(ct.c_double)
        ]
        self.A3200_lib.A3200MotionLinear.restype = ct.c_bool
        
        self.A3200_lib.A3200CommandExecute.argtypes = [
            ct.c_void_p,
            ct.c_uint,
            ct.c_uint32,
            ct.POINTER(ct.c_double)
        ]
        self.A3200_lib.A3200CommandExecute.restype = ct.c_bool

        self.A3200_lib.A3200VariableSetTaskString.argtypes = [
            ct.c_void_p, ct.c_uint, ct.c_uint32, ct.c_char_p
        ]
        self.A3200_lib.A3200VariableSetTaskString.restype = ct.c_bool

        self.A3200_lib.A3200VariableGetTaskString.argtypes = [
            ct.c_void_p, ct.c_uint, ct.c_uint32, ct.c_char_p, ct.c_uint32
        ]
        self.A3200_lib.A3200VariableGetTaskString.restype = ct.c_bool
        
        self.A3200_lib.A3200VariableSetGlobalString.argtypes = [
            ct.c_void_p, ct.c_uint, ct.c_uint32, ct.c_char_p, ct.c_uint32
        ]
        self.A3200_lib.A3200VariableSetGlobalString.restype = ct.c_bool

        self.A3200_lib.A3200VariableSetValueByName.argtypes = [
            ct.c_void_p, ct.c_uint, ct.c_uint32, ct.c_char_p,ct.c_double
        ]
        self.A3200_lib.A3200VariableSetValueByName.restype = ct.c_bool

    def set_task_variables(self, start_index:int, variables:list[float]|None= None, task: int|None=None)  -> list[float]:
        if self.A3200_is_open and not self.simulation:
            task = task if task is not None else self.task
            variables = variables if variables is not None else [1.0]
            c_variables = (DOUBLE * variables)()
            c_start_index = DWORD(start_index)
            c_count = DWORD(len(variables))
            success = self.A3200_lib.A3200VariableSetTaskDoubles(self.handle, task, c_start_index, c_variables, c_count)
            if success:
                return [float(v) for v in c_variables]
            else:
                raise A3200Exception('A3200:get_task_variables','Error occured setting A3200 task variables', 'estop', A3200_DLL=self.A3200_lib)    

    def get_task_variables(self, start_index:int, count:int=1, task: int | None=None)  -> list[float]:
        if self.A3200_is_open and not self.simulation:
            task = task if task is not None else self.task
            c_variables = (DOUBLE * count)()
            c_start_index = DWORD(start_index)
            c_count = DWORD(count)
            success = self.A3200_lib.A3200VariableGetTaskDoubles(self.handle, task, c_start_index, c_count)
            if success:
                return [float(v) for v in c_variables]
            else:
                raise A3200Exception('A3200:get_task_variables','Error occured getting A3200 task variables', 'estop', A3200_DLL=self.A3200_lib) 
            
    def set_global_variables(self, start_index:int, variables:list[float]|None= None)  -> list[float]:
        if self.A3200_is_open and not self.simulation:
            variables = variables if variables is not None else [1.0]
            c_variables = (DOUBLE * variables)()
            c_start_index = DWORD(start_index)
            c_count = DWORD(len(variables))
            success = self.A3200_lib.A3200VariableSetGlobalDoubles(self.handle, c_start_index, c_variables, c_count)
            if success:
                return [float(v) for v in c_variables]
            else:
                raise A3200Exception('A3200:get_task_variables','Error occured setting A3200 global variables', 'estop', A3200_DLL=self.A3200_lib)    

    def get_global_variables(self, start_index:int, count:int=1)  -> list[float]:
        if self.A3200_is_open and not self.simulation:
            c_variables = (DOUBLE * count)()
            c_start_index = DWORD(start_index)
            c_count = DWORD(count)
            success = self.A3200_lib.A3200VariableGetGlobalDoubles(self.handle, c_start_index, c_count)
            if success:
                return [float(v) for v in c_variables]
            else:
                raise A3200Exception('A3200:get_task_variables','Error occured getting A3200 global variables', 'estop', A3200_DLL=self.A3200_lib)    
            
    def set_task_string(self, index:int, string:str, task: int|None=None)  -> bool|None:
        if self.A3200_is_open and not self.simulation:
            task = task if task is not None else self.task
            c_string = ct.create_string_buffer(string.encode('utf-8'))
            c_index = DWORD(index)
            success = self.A3200_lib.A3200VariableSetTaskString(self.handle, task, c_index, c_string)
            if success:
                return success
            else:
                raise A3200Exception('A3200:get_task_variables','Error occured setting A3200 task variables', 'estop', A3200_DLL=self.A3200_lib)    

    def get_task_string(self, index:int, length:int=50, task: int | None=None)  -> str | None:
        if self.A3200_is_open and not self.simulation:
            task = task if task is not None else self.task
            c_string = ct.create_string_buffer(b' '*length)            
            c_index = DWORD(index)
            c_length = DWORD(length)
            success = self.A3200_lib.A3200VariableGetTaskString(self.handle, task, c_index, c_string, c_length)
            if success:
                return c_string.value
            else:
                raise A3200Exception('A3200:get_task_variables','Error occured getting A3200 task variables', 'estop', A3200_DLL=self.A3200_lib) 

    def set_global_string(self, index:int, string:str)  -> bool|None:
        if self.A3200_is_open and not self.simulation:
            c_string = ct.create_string_buffer(string.encode('utf-8'))
            c_index = DWORD(index)
            success = self.A3200_lib.A3200VariableSetGlobalString(self.handle, c_index, c_string)
            if success:
                return success
            else:
                raise A3200Exception('A3200:get_task_variables','Error occured setting A3200 task variables', 'estop', A3200_DLL=self.A3200_lib)    

    def get_global_string(self, index:int, length:int=50)  -> str | None:
        if self.A3200_is_open and not self.simulation:
            c_string = ct.create_string_buffer(b' '*length)            
            c_index = DWORD(index)
            c_length = DWORD(length)
            success = self.A3200_lib.A3200VariableGetGlobalString(self.handle, c_index, c_string, c_length)
            if success:
                return c_string.value
            else:
                raise A3200Exception('A3200:get_task_variables','Error occured getting A3200 task variables', 'estop', A3200_DLL=self.A3200_lib)
            
    def set_variable(self, name:str, value:float, task: int|None=None)-> bool|None:
        if self.A3200_is_open and not self.simulation:
            c_name = ct.create_string_buffer(name.encode('utf-8'))
            c_value = DOUBLE(value)
            return self.A3200_lib.A3200VariableSetByName(self.handle, c_name, c_value)
class A3200Exception(Exception):
    def __init__(self, source, message, level, *args: object, A3200_DLL=None) -> None:
        super().__init__(*args)
        self.source = source
        self.message = message
        self.level = level
        if A3200_DLL is not None:
            bf = 100
            empty = ' '*bf
            error_string = ct.c_buffer(empty.encode('utf-8'))
            buffer_size = ct.c_int(bf)
            A3200_DLL.A3200GetLastErrorString(error_string,buffer_size)
            self.message = f'{message}\n\n{error_string}'
            print(error_string.value)

