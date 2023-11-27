from utils.decorators import route
import server.query as query

@route('search')
def search(uuid, request):
    if request['type'] == 'requirements':
        return requirements(classname=request['value'])
    if request['type'] == 'description':
        return descriptions(classname=request['value'])

def requirements(classname:str):
    return query.get_all_requirements(cls=classname,as_JSON=False)

def descriptions(classname:str):
    return query.get_all_children_descriptions(parent=classname,as_JSON=False)