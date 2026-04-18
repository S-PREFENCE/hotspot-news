Set WshShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' 项目路径
projectDir = "D:\A-ai自动化\hotspot_news"
pythonExe = "python"
appScript = projectDir & "\app.py"

' 清理 __pycache__
For Each objFolder In objFSO.GetFolder(projectDir).SubFolders
    CleanCache objFolder
Next

Sub CleanCache(folder)
    On Error Resume Next
    For Each subFolder In folder.SubFolders
        If LCase(subFolder.Name) = "__pycache__" Then
            subFolder.Delete True
        Else
            CleanCache subFolder
        End If
    Next
End Sub

' 检查端口5000是否已被占用
Set objExec = WshShell.Exec("netstat -ano | findstr "":5000 "" | findstr ""LISTENING""")
strOutput = objExec.StdOut.ReadAll

If InStr(strOutput, ":5000") > 0 Then
    ' 服务已在运行，直接打开浏览器
    WshShell.Run "http://localhost:5000", 1, False
Else
    ' 后台启动Python服务（无黑窗口）
    WshShell.Run "cmd /c cd /d """ & projectDir & """ && " & pythonExe & " """ & appScript & """", 0, False
    ' 等待2秒让服务启动
    WScript.Sleep 2000
    ' 打开浏览器
    WshShell.Run "http://localhost:5000", 1, False
End If
