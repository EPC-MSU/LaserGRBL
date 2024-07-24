using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.IO;
using System.Net;

namespace LaserGRBL.ComWrapper
{
	class XMLRPC : IComWrapper
	{
		private string mAddress;

		private System.Net.Sockets.TcpClient cln;
		BinaryWriter bwriter;
		StreamReader sreader;
		StreamWriter swriter;

		public void Configure(params object[] param)
		{
			mAddress = (string)param[0];
		}

		public void Open()
		{

			if (cln != null)
				Close(true);

			if (string.IsNullOrEmpty(mAddress))
				throw new MissingFieldException("Missing HostName");

			cln = new System.Net.Sockets.TcpClient();
			Logger.LogMessage("OpenCom", "Open {0}", mAddress);
			ComLogger.Log("com", string.Format("Open {0} {1}", mAddress, GetResetDiagnosticString()));

			cln.Connect(IPHelper.Parse(mAddress));

			Stream cst = cln.GetStream();
			bwriter = new BinaryWriter(cst);
			sreader = new StreamReader(cst, Encoding.ASCII);
			swriter = new StreamWriter(cst, Encoding.ASCII);
		}

		private string GetResetDiagnosticString()
		{
			bool soft = Settings.GetObject("Reset Grbl On Connect", false);

			string rv = "";

			if (soft) rv += "Ctrl-X, ";

			return rv.Trim(", ".ToCharArray());
		}

		public void Close(bool auto)
		{
			if (cln != null)
			{
				try
				{
                    ComLogger.Log("com", string.Format("Close {0} [{1}]", mAddress, auto ? "CORE" : "USER"));
					Logger.LogMessage("CloseCom", "Close {0} [{1}]", mAddress, auto ? "CORE" : "USER");
					cln.Close();
				}
				catch { }

				cln = null;
				bwriter = null;
				sreader = null;
				swriter = null;
			}
		}

		public bool IsOpen
		{
			get { return cln != null && cln.Connected; }
		}

		public void Write(byte b)
		{
            ComLogger.Log("tx", b);
			bwriter.Write(b);
			bwriter.Flush();
		}

        public void Write(byte[] arr)
        {
            ComLogger.Log("tx", arr);
            bwriter.Write(arr);
            bwriter.Flush();
        }

        public void Write(string text)
		{
            ComLogger.Log("tx", text);
			swriter.Write(text);
			swriter.Flush();
		}

		public string ReadLineBlocking()
		{
			string rv = null;
			while (IsOpen && rv == null) //wait for disconnect or data
			{
				rv = sreader.ReadLine();

				if (rv == null)
					System.Threading.Thread.Sleep(1);
			}

            ComLogger.Log("rx", rv);
			return rv;
		}

		public bool HasData()
		{ return IsOpen && ((System.Net.Sockets.NetworkStream)sreader.BaseStream).DataAvailable; }

	}
}
