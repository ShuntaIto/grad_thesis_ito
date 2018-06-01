using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.IO;
using System.Windows.Forms;
using NUnit.Framework;
using OpenQA.Selenium;
using OpenQA.Selenium.Chrome;
using System.Text.RegularExpressions;

namespace bAbITranslation
{
	public partial class Form1 : Form
	{
		public Form1()
		{
			InitializeComponent();
		}
	}

	//テキストと教師データ用の数字を分けて格納するクラス
	public class DevidedText
	{
		public string[] Text;
		public string[] DirectNum;
		public string[] FirstNum;
	}

	public class Text
	{
		//テキストを配列に格納
		public string[] ReadText(string path)
		{
			char[] delimiterChars = {'\t','\r','\n' };
			StreamReader sr = new StreamReader(path, Encoding.GetEncoding("Shift_JIS"));
			string text = sr.ReadToEnd();

			string[] lines = text.Split(delimiterChars);

			return lines;
		}

		//監督番号を削除（後に利用できるよう別途格納）
		public DevidedText DeleteDirectNumber(string[] text,string[] firstnum)
		{
			int num = text.Length;
			List<string> list_text = new List<string>();
			List<string> list_num = new List<string>();
			for (int i = 0; i < num; i++)
			{
				if (Regex.IsMatch(text[i],@"^\d+${1,2}"))
				{
					list_num.Add(i + ' ' + text[i]);
				}
				else
				{
					list_text.Add(text[i]);
				}
			}
			DevidedText data = new DevidedText();
			data.Text = list_text.ToArray();
			data.DirectNum = list_num.ToArray();
			data.FirstNum = firstnum;

			return data;
		}


		//文頭の数字を除去（監督番号より先に使用）
		public DevidedText DeleteNumber(string[] rawtext)
		{
			int dim = rawtext.Length;
			string[] text = new string[dim];
			string[] num = new string[dim];
			Regex reg = new Regex(@"^\d{1,2}");
			string pattern = @"^\d{1,2}\s";

			for (int i = 0; i < dim; i++)
			{
				Match m = reg.Match(rawtext[i]);
				num[i] = m.Value;
				text[i] = Regex.Replace(rawtext[i], pattern, "");
			}

			DevidedText data = new DevidedText();
			data.FirstNum = num;
			data.Text = text;
			return data;
		}

		//制限字数（Google翻訳）の範囲内で配列を分割
		public List<string[]> SplitArray(string[] dataset, int strict)
		{
			int num_array = dataset.Length;
			int num = 0;
			List<string[]> splitlist = new List<string[]>();
			List<string> list = new List<string>();

			for (int i = 0; i < num_array; i++)
			{
				num += (dataset[i].Length+1);
				if (num < strict)
				{
					list.Add(dataset[i]);
				}
				else
				{
					string[] part = list.ToArray();
					splitlist.Add(part);
					num = 0;
					list.Clear();
					list.Add(dataset[i]);
				}
			}
			return splitlist;
		}

		//翻訳後のテキストをリストに格納
		public List<string> TextToArray(string text)
		{
			List<string> list = new List<string>();
			System.IO.StringReader rs = new System.IO.StringReader(text);
			while (rs.Peek() > -1)
			{
				list.Add(rs.ReadLine());
			}
			rs.Close();

			return list;
		}

		//翻訳後のデータを元の形に戻す
		public string[] Restoration(string[] origin, DevidedText data,string[] translated)
		{
			int result_dim = origin.Length;
			int num_direct = data.DirectNum.Length;
			int dim = result_dim + num_direct * 2;
			string[] result_temp = new string[dim];

			for (int i = 0; i < num_direct; i++)
			{
				MatchCollection m = Regex.Matches(data.DirectNum[i], @"\d{1,2}");
				int n = Int32.Parse(m[0].Value);
				result_temp[n] = m[1].Value;
			}

			int l = 0;
			for (int i = 0; i <dim; i++)
			{
				if (result_temp[i].Length == 0)
				{
					result_temp[i] = data.Text[i + l];
				}
				else
				{
					l++;
				}
			}

			string[] result = new string[result_dim];
			int k = 0;
			for (int i = 0; i < dim; i++)
			{
				if (Regex.IsMatch(result_temp[i], @"^\d+${1,2}"))
				{
					result[i - 2 - k] = result_temp[i - 2] + " " + "\t" + result_temp[i - 1] + "\t" + result_temp[i];
				}
				else
				{
					k+=2;
				}
			}

			for (int i = 0; i < dim; i++)
			{
				result[i] = data.FirstNum[i] + " " + result[i];
			}

			return result;
		}

		//txtファイルに書き込み
		public void WriteText(string[] text)
		{
			StreamWriter sw = new System.IO.StreamWriter(
							 @"bAbI.txt",
							 false,
							 System.Text.Encoding.GetEncoding("shift_jis"));
			int num = text.Length;
			for (int i = 0; i < num; i++)
			{
				sw.WriteLine(text[i]);
			}
			sw.Close();
		}
	}


	public class WebBrowserControl:Text
	{
		IWebDriver driver = new ChromeDriver();
		[Test]
		public void test()
		{
			string[] data_array = ReadText("data.txt");
			DevidedText data_num_deleted = DeleteNumber(data_array);
			DevidedText data_devided = DeleteDirectNumber(data_num_deleted.Text, data_num_deleted.FirstNum);
			List<string[]> data = SplitArray(data_devided.Text, 1000);
			List<string> result = new List<string>();
			int data_num = data_devided.Text.Length;
			string[] data_translated = new string[data_num];

			int num = data.Count;
			string temp_text = "";
			for (int i = 0; i < 1; i++)
			{
				driver.Navigate().GoToUrl("https://translate.google.co.jp/?hl=ja");
				IWebElement e_data = driver.FindElement(By.CssSelector("#source"));
				IWebElement e_submit = driver.FindElement(By.CssSelector("#gt-submit"));
				IWebElement e_realtime = driver.FindElement(By.CssSelector("#gt-otf-switch"));
				IWebElement e_result = driver.FindElement(By.CssSelector("#result_box"));

				//リアルタイム翻訳を無効化
				e_realtime.SendKeys(OpenQA.Selenium.Keys.Enter);

				int num_array = data[i].Length;
				for (int j = 0; j < num_array; j++)
				{
					e_data.SendKeys(data[i][j]);
					e_data.SendKeys(Environment.NewLine);
				}
				e_submit.SendKeys(OpenQA.Selenium.Keys.Enter);
				temp_text = e_result.Text;
				result.AddRange(TextToArray(temp_text));
			}

			string[] translated = Restoration(data_array,data_devided,result.ToArray());
			WriteText(translated);
			
			Console.WriteLine();
			Console.ReadLine();

			driver.Close();
			driver.Quit();
			
		}
	}
}
