import { useNavigate, useParams } from "react-router-dom";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Plus, Search } from "lucide-react";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { fetchProjects, createProject } from "@/store/projectSlice";
import { fetchWorkspace } from "@/store/workspaceSlice";

export function Projects() {
  const navigate = useNavigate();
  const { workspaceId } = useParams();
  const dispatch = useAppDispatch();
  const { items: projects, loading, error: projectsError } = useAppSelector((state) => state.projects);
  const { error: workspaceError } = useAppSelector((state) => state.workspaces);
  const [searchTerm, setSearchTerm] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");

  useEffect(() => {
    if (workspaceId) {
      dispatch(fetchWorkspace(workspaceId));
      dispatch(fetchProjects({ workspaceId, skip: 0, limit: 100 }));
    }
  }, [workspaceId, dispatch]);

  const handleCreateProject = async () => {
    if (!projectName.trim() || !workspaceId) return;
    
    await dispatch(createProject({ 
      workspaceId,
      data: {
        name: projectName, 
        description: projectDescription 
      }
    }));
    
    setProjectName("");
    setProjectDescription("");
    setDialogOpen(false);
    dispatch(fetchProjects({ workspaceId, skip: 0, limit: 100 }));
  };

  const filteredProjects = projects.filter((project: any) =>
    project.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Search and Actions */}
        <div className="flex gap-4 mb-8">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <Input
              placeholder="Search projects..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button className="bg-gray-900 hover:bg-gray-800 text-white">
                <Plus className="w-4 h-4 mr-2" />
                New Project
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>Create New Project</DialogTitle>
                <DialogDescription>
                  Create a new project in this workspace.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <label htmlFor="name" className="text-sm font-medium">
                    Project Name *
                  </label>
                  <Input
                    id="name"
                    placeholder="Enter project name"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <label htmlFor="description" className="text-sm font-medium">
                    Description
                  </label>
                  <Input
                    id="description"
                    placeholder="Enter project description (optional)"
                    value={projectDescription}
                    onChange={(e) => setProjectDescription(e.target.value)}
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3">
                <Button variant="outline" onClick={() => setDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleCreateProject} disabled={!projectName.trim()} className="bg-gray-900 hover:bg-gray-800 text-white disabled:opacity-50">
                  Create Project
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* Error Messages */}
        {(projectsError || workspaceError) && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{projectsError || workspaceError}</p>
          </div>
        )}

        {/* Projects Grid */}
        {loading ? (
          <div className="text-center py-12">
            <p className="text-gray-600">Loading projects...</p>
          </div>
        ) : filteredProjects.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-600 mb-4">No projects found</p>
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button className="bg-gray-900 hover:bg-gray-800 text-white">Create your first project</Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                  <DialogTitle>Create New Project</DialogTitle>
                  <DialogDescription>
                    Create a new project in this workspace.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid gap-2">
                    <label htmlFor="name" className="text-sm font-medium">
                      Project Name *
                    </label>
                    <Input
                      id="name"
                      placeholder="Enter project name"
                      value={projectName}
                      onChange={(e) => setProjectName(e.target.value)}
                    />
                  </div>
                  <div className="grid gap-2">
                    <label htmlFor="description" className="text-sm font-medium">
                      Description
                    </label>
                    <Input
                      id="description"
                      placeholder="Enter project description (optional)"
                      value={projectDescription}
                      onChange={(e) => setProjectDescription(e.target.value)}
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-3">
                  <Button variant="outline" onClick={() => setDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreateProject} disabled={!projectName.trim()} className="bg-gray-900 hover:bg-gray-800 text-white disabled:opacity-50">
                    Create Project
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredProjects.map((project: any) => (
              <Card
                key={project.id}
                className="hover:shadow-lg transition-shadow cursor-pointer group"
                onClick={() => navigate(`/workspace/${workspaceId}/project/${project.id}`)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="group-hover:text-blue-600 transition-colors">
                        {project.name}
                      </CardTitle>
                      <CardDescription className="mt-2">
                        {project.description || "No description"}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {project.code_config && Object.keys(project.code_config).length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-gray-600 mb-1">Code Config</p>
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(project.code_config).map(([key, value]) => (
                            <Badge key={key} variant="secondary" className="text-xs">
                              {key}: {String(value)}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    {project.scrum_config && Object.keys(project.scrum_config).length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-gray-600 mb-1">Scrum Config</p>
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(project.scrum_config).map(([key, value]) => (
                            <Badge key={key} variant="outline" className="text-xs">
                              {key}: {String(value)}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    <p className="text-xs text-gray-500 pt-2">
                      Created {new Date(project.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
    </main>
  );
}
