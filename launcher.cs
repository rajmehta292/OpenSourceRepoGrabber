using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

namespace OpenSourceRepoGrabberLauncher
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            try
            {
                string projectDir = @"C:\Projects\OpenSourceRepoGrabber";
                
                string exeDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');
                if (File.Exists(Path.Combine(exeDir, "run.py")))
                {
                    projectDir = exeDir;
                }

                string pythonw = Path.Combine(projectDir, @".venv\Scripts\pythonw.exe");
                string python = Path.Combine(projectDir, @".venv\Scripts\python.exe");
                string runPy = Path.Combine(projectDir, "run.py");

                string targetPython = null;
                if (File.Exists(pythonw))
                {
                    targetPython = pythonw;
                }
                else if (File.Exists(python))
                {
                    targetPython = python;
                }

                if (targetPython == null)
                {
                    MessageBox.Show(
                        "Could not find Python virtual environment in:\n" + Path.Combine(projectDir, ".venv") + "\n\nPlease ensure the repository is set up with .venv.",
                        "OpenSource Repo Grabber - Environment Error",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                    return;
                }

                if (!File.Exists(runPy))
                {
                    MessageBox.Show(
                        "Could not find run.py entrypoint in:\n" + projectDir,
                        "OpenSource Repo Grabber - Missing Entrypoint",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                    return;
                }

                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = targetPython;
                psi.Arguments = "\"" + runPy + "\"";
                if (args != null && args.Length > 0)
                {
                    psi.Arguments += " " + string.Join(" ", args);
                }
                psi.WorkingDirectory = projectDir;
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;

                Process.Start(psi);
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "Failed to launch OpenSource Repo Grabber:\n\n" + ex.Message,
                    "OpenSource Repo Grabber - Launch Error",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
        }
    }
}
