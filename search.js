//The recursive search function above is generally looking through nested objects of these types
Parameter = {
    classname: 'string',
    name: 'string',
    description: 'string',
    value: 'Configuration | string | number | boolean | Array[Configuration]',
}

Configuration = {
    classname: 'string',
    name:'string',
    description:'string',
    parameter1: 'Parameter',
    parameter2: 'Parameter',
    parameter3: 'Parameter',
    //... more parameters
}

RootObject = {
    config_type: 'string',
    value: 'Configuration'
}

/**
 * Research function to search through an object.
 * 
 * @param {Object} params - The parameters object.
 * @param {string} params.search_key - The key to search for.
 * @param {Object} params.search_object - The object to search within.
 * @param {string} [params.parent_name] - The name of the parent element.
 * @param {Array} [params.found_items] - Array to store found items.
 * @param {any} [params.search_value] - The value to search for.
 * @param {boolean} [params.find_first=false] - Whether to stop after finding the first match.
 * @param {string | number} [params.idx=''] - Index or identifier for the current search.
 * @param {string} [params.trace=''] - Trace or path of the search.
 */
export const research = ({
    search_key, 
    search_object, 
    parent_name, 
    found_items, 
    search_value, 
    find_first = false, 
    idx = '', 
    trace = ''
}) => {
    // Function implementation
    if(!found_items) found_items = []
    if(search_object === undefined) return found_items
    if(search_object?.classname === 'Parameter') parent_name = search_object?.parent_name
    if(search_object !== undefined && search_object instanceof Object && search_object.hasOwnProperty('config_type')) parent_name = search_object.config_type
    if(search_object !== undefined && search_object instanceof Object && search_object.hasOwnProperty('classname')) trace = `${trace} -> ${search_object.name} ${idx !== '' ? idx+1: ''}`

    Object.keys(search_object).forEach(key=>{
        // Compare each key
        let key_found = false
        if (search_key === undefined) key_found = true //accept any key if search_key not specified
        else if (key === search_key) key_found = true

        // Compare the serach value
        let value_found
        if (search_value === undefined) value_found = true //accept any value if search_value not specified
        else{
            if(search_object[key] instanceof Object && search_value instanceof Object){
                if(_.isEqual(search_object[key], search_value)) value_found = true
            }else if (search_object[key] instanceof Array) {
                if (search_object[key].includes(search_value)) value_found = true
            }else {
                if (search_object[key] === search_value) value_found = true
            }
        }

        if (key_found && value_found){
            // Add item to found_items list if both search_key and search_value are found
            const found_item = {parent_name, parent: search_object, search_key: key, value: search_object[key], trace}
            found_items.push(found_item)
        }else{
            const stop_on_first = find_first && (found_items.length > 0)
            if (!stop_on_first){
                // Recursive search on nested objects
                if (search_object[key] instanceof Array){
                    search_object[key].forEach((_,idx) => {
                        if (search_object[key][idx] instanceof Object) {
                            research({
                                search_key, search_object: search_object[key][idx], parent_name, found_items, search_value, find_first, idx, trace
                            })
                        }
                    })
                }
                else if(search_object[key] instanceof Object){
                    research({
                        search_key,search_object:search_object[key], parent_name, found_items, search_value, find_first, trace
                    })
                }
            }
        }
    })
    return found_items
}




/**
 * Queue-based search function to search through an object.
 * 
 * @param {Object} searchParams - The parameters for the search.
 * @param {string} searchParams.search_key - The key to search for.
 * @param {Object} searchParams.search_object - The object to search within.
 * @param {any} [searchParams.search_value] - The value to search for.
 * @param {boolean} [searchParams.find_first=false] - Whether to stop after finding the first match.
 * @returns {Array} - Array of found items with references to original objects.
 */
export const queue_search = ({
    search_key, 
    search_object, 
    search_value, 
    find_first = false
}) => {
    const found_items = [];
    const queue = [search_object];

    while (queue.length > 0) {
        const current = queue.shift();

        // Process the current object
        if (current && typeof current === 'object') {
            for (const key in current) {
                if (current.hasOwnProperty(key)) {
                    const value = current[key];

                    // Check if the current key and value match the search criteria
                    const key_matches = search_key === undefined || key === search_key;
                    const value_matches = search_value === undefined || value === search_value;

                    if (key_matches && value_matches) {
                        found_items.push({ ...current, search_key: key, value });
                        if (find_first) return found_items;
                    }

                    // Add nested objects to the queue for further processing
                    if (value && typeof value === 'object') {
                        queue.push(value);
                    }
                }
            }
        }
    }

    return found_items;
};