(base) root@DESKTOP-F2PJVJI:~/work/lyss-ai-platform/eino-service# go run cmd/server/main.go
# lyss-ai-platform/eino-service/internal/workflows
internal/workflows/eino_chat.go:218:71: undefined: eino.CompiledChain
internal/workflows/eino_chat.go:224:77: undefined: eino.CompiledChain
internal/workflows/executor.go:142:13: cannot use response (variable of type *WorkflowResponse) as map[string]any value in struct literal
internal/workflows/manager.go:60:35: wm.registry.GetWorkflowCount undefined (type WorkflowRegistry has no field or method GetWorkflowCount)
internal/workflows/manager.go:61:35: wm.registry.GetWorkflowNames undefined (type WorkflowRegistry has no field or method GetWorkflowNames)
internal/workflows/manager.go:71:56: cannot use simpleChatWorkflow (variable of type *SimpleChatWorkflow) as WorkflowEngine value in argument to wm.registry.RegisterWorkflow: *SimpleChatWorkflow does not implement WorkflowEngine (missing method ExecuteStream)
internal/workflows/manager.go:160:21: wm.registry.GetWorkflowInfo undefined (type WorkflowRegistry has no field or method GetWorkflowInfo)
internal/workflows/manager.go:236:21: wm.registry.UnregisterWorkflow undefined (type WorkflowRegistry has no field or method UnregisterWorkflow)
internal/workflows/registry.go:63:43: workflow.GetWorkflowInfo undefined (type WorkflowEngine has no field or method GetWorkflowInfo)
internal/workflows/registry.go:127:19: workflow.GetWorkflowInfo undefined (type WorkflowEngine has no field or method GetWorkflowInfo)
internal/workflows/registry.go:127:19: too many errors
(base) root@DESKTOP-F2PJVJI:~/work/lyss-ai-platform/eino-service# 