import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  BarElement,
  LinearScale,
  CategoryScale,
  Tooltip,
  Legend,
} from 'chart.js'
import annotationPlugin from 'chartjs-plugin-annotation'

let registered = false

/** Idempotent. Imported once from each chart component to register Chart.js
 *  components and the annotation plugin globally. */
export function ensureChartJsRegistered(): void {
  if (registered) return
  ChartJS.register(
    LineElement,
    PointElement,
    BarElement,
    LinearScale,
    CategoryScale,
    Tooltip,
    Legend,
    annotationPlugin,
  )
  registered = true
}
