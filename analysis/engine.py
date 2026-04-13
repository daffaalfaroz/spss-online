"""
SPSS Online - Statistical Analysis Engine
Covers all 21 analysis types from the menu.
"""
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.multivariate.manova import MANOVA
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from factor_analyzer import FactorAnalyzer
import warnings
warnings.filterwarnings('ignore')


def fmt(val, decimals=4):
    """Format a number nicely."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return '.'
    if isinstance(val, float):
        return f"{val:.{decimals}f}"
    return str(val)


def sig_stars(p):
    if p < 0.001:
        return '***'
    elif p < 0.01:
        return '**'
    elif p < 0.05:
        return '*'
    return ''


def make_table(headers, rows, title='', caption=''):
    """Generate HTML table for output viewer."""
    html = f'<div class="output-table-block">'
    if title:
        html += f'<div class="output-table-title">{title}</div>'
    if caption:
        html += f'<div class="output-table-caption">{caption}</div>'
    html += '<table class="output-table"><thead><tr>'
    for h in headers:
        html += f'<th>{h}</th>'
    html += '</tr></thead><tbody>'
    for row in rows:
        html += '<tr>'
        for cell in row:
            html += f'<td>{cell}</td>'
        html += '</tr>'
    html += '</tbody></table></div>'
    return html


def make_note(text):
    return f'<div class="output-note"><span class="note-label">a.</span> {text}</div>'


class AnalysisEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def get_numeric_cols(self):
        return list(self.df.select_dtypes(include=[np.number]).columns)

    # ─── 1. DESKRIPTIF ───────────────────────────────────────────────────────

    def descriptive(self, variables, options=None):
        opts = options or {}
        df = self.df[variables].copy()
        output = '<div class="output-block"><div class="output-title">Descriptive Statistics</div>'

        rows = []
        for var in variables:
            col = df[var].dropna()
            n = len(col)
            mean = col.mean()
            median = col.median()
            try:
                mode_val = col.mode()[0]
            except Exception:
                mode_val = np.nan
            std = col.std()
            variance = col.var()
            se = std / np.sqrt(n) if n > 0 else np.nan
            minimum = col.min()
            maximum = col.max()
            rng = maximum - minimum
            sk = col.skew()
            ku = col.kurt()
            q1 = col.quantile(0.25)
            q3 = col.quantile(0.75)
            missing = self.df[var].isna().sum()
            rows.append([
                var, n, missing, fmt(mean), fmt(median), fmt(mode_val),
                fmt(std), fmt(variance), fmt(se), fmt(minimum), fmt(maximum),
                fmt(rng), fmt(q1), fmt(q3), fmt(sk), fmt(ku)
            ])

        headers = ['Variable', 'N', 'Missing', 'Mean', 'Median', 'Mode',
                   'Std Dev', 'Variance', 'Std Error', 'Min', 'Max', 'Range',
                   'Q1 (25%)', 'Q3 (75%)', 'Skewness', 'Kurtosis']
        output += make_table(headers, rows, title='Descriptive Statistics')
        output += make_note('Based on non-missing observations.')
        output += '</div>'
        return output

    # ─── 2. FREKUENSI ────────────────────────────────────────────────────────

    def frequencies(self, variables, options=None):
        output = '<div class="output-block"><div class="output-title">Frequencies</div>'
        for var in variables:
            col = self.df[var]
            total = len(col)
            vc = col.value_counts(dropna=False).reset_index()
            vc.columns = ['Value', 'Frequency']
            vc['Percent'] = (vc['Frequency'] / total * 100).map(lambda x: fmt(x, 2) + '%')
            valid_total = col.notna().sum()
            vc['Valid Percent'] = vc.apply(
                lambda r: fmt(r['Frequency'] / valid_total * 100, 2) + '%' if pd.notna(r['Value']) else '.', axis=1
            )
            cum = 0
            cum_pcts = []
            for i, row in vc.iterrows():
                if pd.notna(row['Value']):
                    cum += row['Frequency']
                    cum_pcts.append(fmt(cum / valid_total * 100, 2) + '%')
                else:
                    cum_pcts.append('.')
            vc['Cumulative %'] = cum_pcts

            rows = [[str(r['Value']), r['Frequency'], r['Percent'], r['Valid Percent'], r['Cumulative %']]
                    for _, r in vc.iterrows()]

            # Add Total row
            rows.append(['<strong>Total</strong>', total, '100.00%', '100.00%', '100.00%'])

            output += make_table(
                ['Value', 'Frequency', 'Percent', 'Valid Percent', 'Cumulative %'],
                rows, title=f'Frequency Table: {var}'
            )
        output += '</div>'
        return output

    # ─── 3. CROSSTAB ─────────────────────────────────────────────────────────

    def crosstab(self, row_var, col_var, options=None):
        output = '<div class="output-block"><div class="output-title">Crosstabulation</div>'
        ct = pd.crosstab(self.df[row_var], self.df[col_var], margins=True, margins_name='Total')
        headers = [''] + [str(c) for c in ct.columns]
        rows = []
        for idx, row in ct.iterrows():
            rows.append([str(idx)] + [str(v) for v in row])
        output += make_table(headers, rows, title=f'{row_var} × {col_var} Crosstabulation')

        # Chi-square test
        ct_no_margin = pd.crosstab(self.df[row_var], self.df[col_var])
        chi2, p, dof, expected = stats.chi2_contingency(ct_no_margin)
        n = len(self.df)
        phi = np.sqrt(chi2 / n)
        cramers_v = np.sqrt(chi2 / (n * (min(ct_no_margin.shape) - 1)))
        chi_rows = [
            ['Pearson Chi-Square', fmt(chi2), dof, fmt(p), sig_stars(p)],
            ["Phi", fmt(phi), '', '', ''],
            ["Cramer's V", fmt(cramers_v), '', '', ''],
        ]
        output += make_table(
            ['Statistic', 'Value', 'df', 'Sig. (2-tailed)', ''],
            chi_rows, title='Chi-Square Tests'
        )
        output += make_note(f'N = {n}')
        output += '</div>'
        return output

    # ─── 4. T-TEST INDEPENDEN ─────────────────────────────────────────────────

    def ttest_independent(self, dep_var, group_var, group1, group2, options=None):
        output = '<div class="output-block"><div class="output-title">Independent Samples T-Test</div>'
        df = self.df.copy()
        g1 = df[df[group_var].astype(str) == str(group1)][dep_var].dropna()
        g2 = df[df[group_var].astype(str) == str(group2)][dep_var].dropna()

        # Group Statistics
        gs_rows = [
            [str(group1), len(g1), fmt(g1.mean()), fmt(g1.std()), fmt(g1.std()/np.sqrt(len(g1)))],
            [str(group2), len(g2), fmt(g2.mean()), fmt(g2.std()), fmt(g2.std()/np.sqrt(len(g2)))],
        ]
        output += make_table(
            ['Group', 'N', 'Mean', 'Std Deviation', 'Std Error Mean'],
            gs_rows, title=f'Group Statistics: {dep_var}'
        )

        # Levene's test
        lev_stat, lev_p = stats.levene(g1, g2)
        # Equal variance assumed
        t_eq, p_eq = stats.ttest_ind(g1, g2, equal_var=True)
        df_eq = len(g1) + len(g2) - 2
        mean_diff = g1.mean() - g2.mean()
        se_eq = np.sqrt(g1.var(ddof=1)/len(g1) + g2.var(ddof=1)/len(g2))
        ci_eq = stats.t.interval(0.95, df_eq, loc=mean_diff, scale=se_eq)
        # Unequal variance (Welch)
        t_ne, p_ne = stats.ttest_ind(g1, g2, equal_var=False)
        df_ne = (g1.var(ddof=1)/len(g1) + g2.var(ddof=1)/len(g2))**2 / \
                ((g1.var(ddof=1)/len(g1))**2/(len(g1)-1) + (g2.var(ddof=1)/len(g2))**2/(len(g2)-1))
        ci_ne = stats.t.interval(0.95, df_ne, loc=mean_diff, scale=se_eq)

        # Effect size (Cohen's d)
        pooled_sd = np.sqrt(((len(g1)-1)*g1.std()**2 + (len(g2)-1)*g2.std()**2) / (len(g1)+len(g2)-2))
        cohens_d = mean_diff / pooled_sd if pooled_sd > 0 else np.nan

        t_rows = [
            ['Equal var assumed', fmt(lev_stat, 3), fmt(lev_p, 3), fmt(t_eq, 3), df_eq,
             fmt(p_eq, 3), sig_stars(p_eq), fmt(mean_diff), fmt(ci_eq[0]), fmt(ci_eq[1])],
            ['Equal var not assumed', '', '', fmt(t_ne, 3), fmt(df_ne, 2),
             fmt(p_ne, 3), sig_stars(p_ne), fmt(mean_diff), fmt(ci_ne[0]), fmt(ci_ne[1])],
        ]
        output += make_table(
            ['', "Levene's F", "Levene's Sig.", 't', 'df', 'Sig. (2-tailed)', '',
             'Mean Diff', '95% CI Lower', '95% CI Upper'],
            t_rows, title='Independent Samples Test'
        )
        output += make_note(f"Cohen's d = {fmt(cohens_d, 3)}")
        output += '</div>'
        return output

    # ─── 5. T-TEST 1 SAMPEL ───────────────────────────────────────────────────

    def ttest_onesample(self, variables, test_value=0, options=None):
        output = '<div class="output-block"><div class="output-title">One-Sample T-Test</div>'
        gs_rows = []
        for var in variables:
            col = self.df[var].dropna()
            gs_rows.append([var, len(col), fmt(col.mean()), fmt(col.std()), fmt(col.std()/np.sqrt(len(col)))])
        output += make_table(
            ['Variable', 'N', 'Mean', 'Std Deviation', 'Std Error Mean'],
            gs_rows, title='One-Sample Statistics'
        )

        t_rows = []
        for var in variables:
            col = self.df[var].dropna()
            t, p = stats.ttest_1samp(col, test_value)
            df_val = len(col) - 1
            ci = stats.t.interval(0.95, df_val, loc=col.mean() - test_value, scale=col.std()/np.sqrt(len(col)))
            t_rows.append([var, fmt(t), df_val, fmt(p), sig_stars(p),
                           fmt(col.mean() - test_value), fmt(ci[0]), fmt(ci[1])])
        output += make_table(
            ['Variable', 't', 'df', 'Sig. (2-tailed)', '', 'Mean Diff', '95% CI Lower', '95% CI Upper'],
            t_rows, title=f'One-Sample Test (Test Value = {test_value})'
        )
        output += '</div>'
        return output

    # ─── 6. T-TEST BERPASANGAN ────────────────────────────────────────────────

    def ttest_paired(self, pairs, options=None):
        output = '<div class="output-block"><div class="output-title">Paired Samples T-Test</div>'
        gs_rows = []
        for v1, v2 in pairs:
            for v in [v1, v2]:
                col = self.df[v].dropna()
                gs_rows.append([v, len(col), fmt(col.mean()), fmt(col.std()), fmt(col.std()/np.sqrt(len(col)))])
        output += make_table(['Variable', 'N', 'Mean', 'Std Deviation', 'Std Error Mean'],
                             gs_rows, title='Paired Samples Statistics')

        t_rows = []
        for v1, v2 in pairs:
            merged = self.df[[v1, v2]].dropna()
            diff = merged[v1] - merged[v2]
            t, p = stats.ttest_rel(merged[v1], merged[v2])
            n = len(merged)
            df_val = n - 1
            ci = stats.t.interval(0.95, df_val, loc=diff.mean(), scale=diff.std()/np.sqrt(n))
            t_rows.append([f'{v1} - {v2}', fmt(diff.mean()), fmt(diff.std()),
                           fmt(diff.std()/np.sqrt(n)), fmt(ci[0]), fmt(ci[1]), fmt(t), df_val, fmt(p), sig_stars(p)])
        output += make_table(
            ['Pair', 'Mean Diff', 'Std Dev', 'Std Error', '95% CI Lower', '95% CI Upper',
             't', 'df', 'Sig. (2-tailed)', ''],
            t_rows, title='Paired Samples Test'
        )
        output += '</div>'
        return output

    # ─── 7. ANOVA SATU ARAH ───────────────────────────────────────────────────

    def anova_oneway(self, dep_var, factor_var, options=None):
        output = '<div class="output-block"><div class="output-title">One-Way ANOVA</div>'
        groups = [grp[dep_var].dropna().values
                  for _, grp in self.df.groupby(factor_var) if len(grp[dep_var].dropna()) > 0]
        f_stat, p_val = stats.f_oneway(*groups)
        grand_mean = self.df[dep_var].dropna().mean()
        n_total = sum(len(g) for g in groups)
        k = len(groups)
        ss_between = sum(len(g) * (g.mean() - grand_mean)**2 for g in groups)
        ss_within = sum(((g - g.mean())**2).sum() for g in groups)
        ss_total = ss_between + ss_within
        df_between = k - 1
        df_within = n_total - k
        ms_between = ss_between / df_between
        ms_within = ss_within / df_within

        anova_rows = [
            ['Between Groups', fmt(ss_between), df_between, fmt(ms_between), fmt(f_stat), fmt(p_val), sig_stars(p_val)],
            ['Within Groups', fmt(ss_within), df_within, fmt(ms_within), '', '', ''],
            ['Total', fmt(ss_total), n_total - 1, '', '', '', ''],
        ]
        output += make_table(
            ['Source', 'Sum of Squares', 'df', 'Mean Square', 'F', 'Sig.', ''],
            anova_rows, title=f'ANOVA: {dep_var}'
        )

        # Group descriptives
        desc_rows = []
        for name, grp in self.df.groupby(factor_var):
            col = grp[dep_var].dropna()
            desc_rows.append([str(name), len(col), fmt(col.mean()), fmt(col.std()),
                              fmt(col.std()/np.sqrt(len(col))), fmt(col.min()), fmt(col.max())])
        output += make_table(
            ['Group', 'N', 'Mean', 'Std Dev', 'Std Error', 'Min', 'Max'],
            desc_rows, title='Group Descriptives'
        )

        # Eta-squared
        eta2 = ss_between / ss_total
        output += make_note(f"η² (Eta-squared) = {fmt(eta2, 4)}")
        output += '</div>'
        return output

    # ─── 8. ANOVA DUA ARAH ────────────────────────────────────────────────────

    def anova_twoway(self, dep_var, factor1, factor2, options=None):
        output = '<div class="output-block"><div class="output-title">Two-Way ANOVA</div>'
        data = self.df[[dep_var, factor1, factor2]].dropna().copy()
        data[factor1] = data[factor1].astype('category')
        data[factor2] = data[factor2].astype('category')
        formula = f'Q("{dep_var}") ~ C(Q("{factor1}")) + C(Q("{factor2}")) + C(Q("{factor1}")):C(Q("{factor2}"))'
        try:
            model = ols(formula, data=data).fit()
            anova_table = sm.stats.anova_lm(model, typ=2)
            rows = []
            for src, row in anova_table.iterrows():
                rows.append([src, fmt(row.get('sum_sq', np.nan)), fmt(row.get('df', np.nan)),
                             fmt(row.get('sum_sq', 0)/row.get('df', 1) if row.get('df', 0) != 0 else np.nan),
                             fmt(row.get('F', np.nan)), fmt(row.get('PR(>F)', np.nan)),
                             sig_stars(row.get('PR(>F)', 1)) if pd.notna(row.get('PR(>F)', np.nan)) else ''])
            output += make_table(['Source', 'SS', 'df', 'MS', 'F', 'Sig.', ''], rows, title='Tests of Between-Subjects Effects')
        except Exception as e:
            output += f'<div class="output-error">Error: {str(e)}</div>'
        output += '</div>'
        return output

    # ─── 9. MANOVA ────────────────────────────────────────────────────────────

    def manova(self, dep_vars, factor_var, options=None):
        output = '<div class="output-block"><div class="output-title">MANOVA</div>'
        data = self.df[dep_vars + [factor_var]].dropna().copy()
        dep_str = ' + '.join([f'Q("{v}")' for v in dep_vars])
        formula = f'{dep_str} ~ C(Q("{factor_var}"))'
        try:
            mv = MANOVA.from_formula(formula, data=data)
            result = mv.mv_test()
            output += f'<div class="output-pre">{str(result)}</div>'
        except Exception as e:
            output += f'<div class="output-error">Error: {str(e)}</div>'
        output += '</div>'
        return output

    # ─── 10. KORELASI PEARSON ─────────────────────────────────────────────────

    def correlation_pearson(self, variables, options=None):
        return self._correlation(variables, method='pearson')

    # ─── 11. KORELASI SPEARMAN ────────────────────────────────────────────────

    def correlation_spearman(self, variables, options=None):
        return self._correlation(variables, method='spearman')

    def _correlation(self, variables, method='pearson'):
        label = 'Pearson' if method == 'pearson' else 'Spearman'
        output = f'<div class="output-block"><div class="output-title">{label} Correlation</div>'
        df = self.df[variables].dropna()
        n = len(df)

        corr_matrix = []
        p_matrix = []
        for v1 in variables:
            row_r = []
            row_p = []
            for v2 in variables:
                if method == 'pearson':
                    r, p = stats.pearsonr(df[v1], df[v2])
                else:
                    r, p = stats.spearmanr(df[v1], df[v2])
                row_r.append(r)
                row_p.append(p)
            corr_matrix.append(row_r)
            p_matrix.append(row_p)

        # Build table: r and p for each pair
        headers = ['Variable'] + variables
        rows = []
        for i, v1 in enumerate(variables):
            r_row = [f'<strong>{v1}</strong>']
            for j, v2 in enumerate(variables):
                r = corr_matrix[i][j]
                p = p_matrix[i][j]
                if i == j:
                    r_row.append('1.000')
                else:
                    r_row.append(f'{fmt(r, 3)}<br><small>p={fmt(p, 3)}{sig_stars(p)}</small>')
            rows.append(r_row)
        output += make_table(headers, rows, title=f'{label} Correlation Matrix (N={n})')
        output += make_note('** Significant at p < 0.01, * Significant at p < 0.05.')
        output += '</div>'
        return output

    # ─── 12. REGRESI LINEAR ───────────────────────────────────────────────────

    def regression_linear(self, dep_var, indep_vars, options=None):
        output = '<div class="output-block"><div class="output-title">Linear Regression</div>'
        data = self.df[[dep_var] + indep_vars].dropna()
        X = sm.add_constant(data[indep_vars])
        y = data[dep_var]
        try:
            model = sm.OLS(y, X).fit()
            r2 = model.rsquared
            r2_adj = model.rsquared_adj
            f_stat = model.fvalue
            f_p = model.f_pvalue
            n = len(data)
            k = len(indep_vars)

            summary_rows = [
                ['R', fmt(np.sqrt(r2), 4)],
                ['R Square', fmt(r2, 4)],
                ['Adjusted R Square', fmt(r2_adj, 4)],
                ['Std. Error of Estimate', fmt(np.sqrt(model.mse_resid), 4)],
                ['N', n],
                ['F Statistic', fmt(f_stat, 4)],
                ['F Significance', fmt(f_p, 4) + ' ' + sig_stars(f_p)],
            ]
            output += make_table(['Statistic', 'Value'], summary_rows, title='Model Summary')

            # ANOVA table
            ss_reg = model.mse_model * k
            ss_res = model.mse_resid * (n - k - 1)
            anova_rows = [
                ['Regression', fmt(ss_reg), k, fmt(model.mse_model), fmt(f_stat), fmt(f_p), sig_stars(f_p)],
                ['Residual', fmt(ss_res), n - k - 1, fmt(model.mse_resid), '', '', ''],
                ['Total', fmt(ss_reg + ss_res), n - 1, '', '', '', ''],
            ]
            output += make_table(['', 'Sum of Squares', 'df', 'Mean Square', 'F', 'Sig.', ''],
                                 anova_rows, title='ANOVA')

            # Coefficients
            coef_rows = []
            for i, name in enumerate(model.params.index):
                b = model.params[name]
                se = model.bse[name]
                t = model.tvalues[name]
                p = model.pvalues[name]
                ci = model.conf_int().loc[name]
                beta = model.params[name] * (data[name].std() / y.std()) if name != 'const' else np.nan
                coef_rows.append([
                    name, fmt(b), fmt(se), fmt(beta) if name != 'const' else '.',
                    fmt(t), fmt(p), sig_stars(p), fmt(ci[0]), fmt(ci[1])
                ])
            output += make_table(
                ['Variable', 'B', 'Std Error', 'Beta', 't', 'Sig.', '', '95% CI Lower', '95% CI Upper'],
                coef_rows, title='Coefficients'
            )
            output += make_note(f'Dependent variable: {dep_var}')
        except Exception as e:
            output += f'<div class="output-error">Error: {str(e)}</div>'
        output += '</div>'
        return output

    # ─── 13. REGRESI LOGISTIK ─────────────────────────────────────────────────

    def regression_logistic(self, dep_var, indep_vars, options=None):
        output = '<div class="output-block"><div class="output-title">Logistic Regression</div>'
        data = self.df[[dep_var] + indep_vars].dropna()
        X = sm.add_constant(data[indep_vars])
        y = data[dep_var]
        try:
            model = sm.Logit(y, X).fit(disp=0)
            n = len(data)

            summary_rows = [
                ['-2 Log Likelihood', fmt(-2 * model.llf)],
                ['Cox & Snell R²', fmt(1 - np.exp(-(model.llr) * 2 / n))],
                ['Nagelkerke R²', fmt((1 - np.exp(-model.llr * 2 / n)) / (1 - np.exp(2 * model.llnull / n)))],
                ['N', n],
            ]
            output += make_table(['Statistic', 'Value'], summary_rows, title='Model Summary')

            coef_rows = []
            for name in model.params.index:
                b = model.params[name]
                se = model.bse[name]
                wald = (b / se)**2
                p = model.pvalues[name]
                exp_b = np.exp(b)
                coef_rows.append([name, fmt(b), fmt(se), fmt(wald), 1, fmt(p), sig_stars(p), fmt(exp_b)])
            output += make_table(
                ['Variable', 'B', 'S.E.', 'Wald', 'df', 'Sig.', '', 'Exp(B)'],
                coef_rows, title='Variables in the Equation'
            )
            output += make_note(f'Dependent variable: {dep_var}')
        except Exception as e:
            output += f'<div class="output-error">Error: {str(e)}</div>'
        output += '</div>'
        return output

    # ─── 14. UJI NORMALITAS ───────────────────────────────────────────────────

    def normality(self, variables, options=None):
        output = '<div class="output-block"><div class="output-title">Tests of Normality</div>'
        rows = []
        for var in variables:
            col = self.df[var].dropna()
            n = len(col)
            # Shapiro-Wilk (best for n < 2000)
            if n <= 5000:
                sw_stat, sw_p = stats.shapiro(col)
            else:
                sw_stat, sw_p = np.nan, np.nan
            # Kolmogorov-Smirnov
            ks_stat, ks_p = stats.kstest(col, 'norm', args=(col.mean(), col.std()))
            # Anderson-Darling
            ad_result = stats.anderson(col)
            ad_stat = ad_result.statistic
            # Skewness & Kurtosis
            sk = col.skew()
            ku = col.kurt()
            normal_verdict = '✅ Normal' if (sw_p > 0.05 if pd.notna(sw_p) else True) else '❌ Not Normal'
            rows.append([
                var, n,
                fmt(sw_stat, 4), fmt(sw_p, 4), sig_stars(sw_p) if pd.notna(sw_p) else '',
                fmt(ks_stat, 4), fmt(ks_p, 4), sig_stars(ks_p),
                fmt(sk, 4), fmt(ku, 4),
                normal_verdict
            ])
        output += make_table(
            ['Variable', 'N',
             'Shapiro-Wilk W', 'S-W Sig.', '',
             'K-S Stat', 'K-S Sig.', '',
             'Skewness', 'Kurtosis', 'Verdict'],
            rows, title='Tests of Normality'
        )
        output += make_note('Shapiro-Wilk recommended for n < 2000. Significance < 0.05 = not normal.')
        output += '</div>'
        return output

    # ─── 15. CHI-SQUARE ───────────────────────────────────────────────────────

    def chi_square(self, row_var, col_var, options=None):
        return self.crosstab(row_var, col_var, options)

    # ─── 16. MANN-WHITNEY U ───────────────────────────────────────────────────

    def mann_whitney(self, dep_var, group_var, group1, group2, options=None):
        output = '<div class="output-block"><div class="output-title">Mann-Whitney U Test</div>'
        g1 = self.df[self.df[group_var].astype(str) == str(group1)][dep_var].dropna()
        g2 = self.df[self.df[group_var].astype(str) == str(group2)][dep_var].dropna()

        gs_rows = [
            [str(group1), len(g1), fmt(g1.mean()), fmt(g1.median()), fmt(g1.std())],
            [str(group2), len(g2), fmt(g2.mean()), fmt(g2.median()), fmt(g2.std())],
        ]
        output += make_table(['Group', 'N', 'Mean', 'Median', 'Std Dev'],
                             gs_rows, title='Group Statistics')

        u_stat, p_val = stats.mannwhitneyu(g1, g2, alternative='two-sided')
        z = (u_stat - len(g1) * len(g2) / 2) / np.sqrt(len(g1) * len(g2) * (len(g1) + len(g2) + 1) / 12)
        r = abs(z) / np.sqrt(len(g1) + len(g2))  # Effect size r

        test_rows = [
            ['Mann-Whitney U', fmt(u_stat, 3)],
            ['Z', fmt(z, 3)],
            ['Asymp. Sig. (2-tailed)', fmt(p_val, 4) + ' ' + sig_stars(p_val)],
            ['Effect Size r', fmt(r, 4)],
        ]
        output += make_table(['Statistic', 'Value'], test_rows, title='Test Statistics')
        output += make_note(f'Variable: {dep_var}')
        output += '</div>'
        return output

    # ─── 17. WILCOXON ─────────────────────────────────────────────────────────

    def wilcoxon(self, var1, var2, options=None):
        output = '<div class="output-block"><div class="output-title">Wilcoxon Signed-Rank Test</div>'
        merged = self.df[[var1, var2]].dropna()
        diff = merged[var1] - merged[var2]
        n = len(merged)

        stat, p = stats.wilcoxon(merged[var1], merged[var2])
        z = (stat - n*(n+1)/4) / np.sqrt(n*(n+1)*(2*n+1)/24)
        r = abs(z) / np.sqrt(n)

        neg = (diff < 0).sum()
        pos = (diff > 0).sum()
        ties = (diff == 0).sum()

        ranks_rows = [
            ['Negative Ranks', neg, '', ''],
            ['Positive Ranks', pos, '', ''],
            ['Ties', ties, '', ''],
            ['Total', n, '', ''],
        ]
        output += make_table(['', 'N', 'Mean Rank', 'Sum of Ranks'], ranks_rows,
                             title=f'Ranks: {var2} - {var1}')

        test_rows = [
            ['Wilcoxon W', fmt(stat)],
            ['Z', fmt(z)],
            ['Asymp. Sig. (2-tailed)', fmt(p, 4) + ' ' + sig_stars(p)],
            ['Effect Size r', fmt(r, 4)],
        ]
        output += make_table(['Statistic', 'Value'], test_rows, title='Test Statistics')
        output += '</div>'
        return output

    # ─── 18. KRUSKAL-WALLIS ───────────────────────────────────────────────────

    def kruskal_wallis(self, dep_var, group_var, options=None):
        output = '<div class="output-block"><div class="output-title">Kruskal-Wallis Test</div>'
        groups = [grp[dep_var].dropna().values for _, grp in self.df.groupby(group_var)]
        h_stat, p_val = stats.kruskal(*groups)
        k = len(groups)
        n = sum(len(g) for g in groups)
        eta2 = (h_stat - k + 1) / (n - k)

        gs_rows = []
        for name, grp in self.df.groupby(group_var):
            col = grp[dep_var].dropna()
            gs_rows.append([str(name), len(col), fmt(col.mean()), fmt(col.median()), fmt(col.std())])
        output += make_table(['Group', 'N', 'Mean', 'Median', 'Std Dev'], gs_rows, title='Group Statistics')

        test_rows = [
            ['Kruskal-Wallis H', fmt(h_stat)],
            ['df', k - 1],
            ['Asymp. Sig.', fmt(p_val, 4) + ' ' + sig_stars(p_val)],
            ['Eta-squared (η²)', fmt(eta2, 4)],
        ]
        output += make_table(['Statistic', 'Value'], test_rows, title='Test Statistics')
        output += make_note(f'Grouping variable: {group_var}')
        output += '</div>'
        return output

    # ─── 19. ANALISIS FAKTOR ──────────────────────────────────────────────────

    def factor_analysis(self, variables, n_factors=None, options=None):
        output = '<div class="output-block"><div class="output-title">Factor Analysis</div>'
        data = self.df[variables].dropna()
        n_vars = len(variables)
        if n_factors is None:
            n_factors = max(1, n_vars // 2)
        n_factors = min(n_factors, n_vars - 1)

        try:
            fa = FactorAnalyzer(n_factors=n_factors, rotation='varimax', method='principal')
            fa.fit(data)
            ev, v = fa.get_eigenvalues()
            loadings = fa.loadings_
            communalities = fa.get_communalities()
            variance = fa.get_factor_variance()

            # Eigenvalues table
            ev_rows = [[i+1, fmt(ev[i]), fmt(ev[i]/n_vars*100, 2)+'%', fmt(ev[:i+1].sum()/n_vars*100, 2)+'%']
                       for i in range(n_vars)]
            output += make_table(['Factor', 'Eigenvalue', '% of Variance', 'Cumulative %'],
                                 ev_rows, title='Total Variance Explained')

            # Loadings
            fac_headers = ['Variable'] + [f'Factor {i+1}' for i in range(n_factors)] + ['Communality']
            load_rows = [[variables[i]] + [fmt(loadings[i, j]) for j in range(n_factors)] + [fmt(communalities[i])]
                         for i in range(n_vars)]
            output += make_table(fac_headers, load_rows, title='Rotated Component Matrix (Varimax)')
        except Exception as e:
            output += f'<div class="output-error">Error: {str(e)}</div>'
        output += '</div>'
        return output

    # ─── 20. ANALISIS KLASTER ─────────────────────────────────────────────────

    def cluster_analysis(self, variables, n_clusters=3, options=None):
        output = '<div class="output-block"><div class="output-title">Cluster Analysis (K-Means)</div>'
        data = self.df[variables].dropna()
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(data)

        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        km.fit(X_scaled)
        labels = km.labels_
        inertia = km.inertia_

        # Cluster sizes
        unique, counts = np.unique(labels, return_counts=True)
        size_rows = [[f'Cluster {c+1}', cnt, fmt(cnt/len(data)*100, 2)+'%']
                     for c, cnt in zip(unique, counts)]
        size_rows.append(['Total', len(data), '100.00%'])
        output += make_table(['Cluster', 'N', 'Percent'], size_rows, title='Cluster Memberships')

        # Cluster centers
        centers = scaler.inverse_transform(km.cluster_centers_)
        cent_headers = ['Variable'] + [f'Cluster {i+1}' for i in range(n_clusters)]
        cent_rows = [[variables[i]] + [fmt(centers[j, i]) for j in range(n_clusters)]
                     for i in range(len(variables))]
        output += make_table(cent_headers, cent_rows, title='Final Cluster Centers')
        output += make_note(f'Inertia (WCSS) = {fmt(inertia)} | {n_clusters} clusters | Standardized variables.')
        output += '</div>'
        return output

    # ─── 21. RELIABILITAS ALPHA ───────────────────────────────────────────────

    def reliability_alpha(self, variables, options=None):
        output = '<div class="output-block"><div class="output-title">Reliability Analysis (Cronbach\'s Alpha)</div>'
        data = self.df[variables].dropna()
        k = len(variables)
        n = len(data)

        # Cronbach's Alpha
        item_variances = data.var(ddof=1)
        total_variance = data.sum(axis=1).var(ddof=1)
        alpha = (k / (k - 1)) * (1 - item_variances.sum() / total_variance)

        summary_rows = [
            ['Cronbach\'s Alpha', fmt(alpha, 4)],
            ['N of Items', k],
            ['N (cases)', n],
        ]
        output += make_table(['Statistic', 'Value'], summary_rows, title='Reliability Statistics')

        # Item-Total Statistics
        item_rows = []
        for var in variables:
            others = [v for v in variables if v != var]
            rest = data[others].sum(axis=1)
            r_total = data[var].corr(data.sum(axis=1))
            r_corrected = data[var].corr(rest)
            # Alpha if item deleted
            sub_data = data[others]
            sub_k = len(others)
            sub_var = sub_data.var(ddof=1)
            sub_total_var = sub_data.sum(axis=1).var(ddof=1)
            alpha_if_deleted = (sub_k / (sub_k - 1)) * (1 - sub_var.sum() / sub_total_var) if sub_k > 1 else np.nan
            item_rows.append([var, fmt(data[var].mean(), 4), fmt(data[var].std(), 4),
                              fmt(r_total, 4), fmt(r_corrected, 4), fmt(alpha_if_deleted, 4)])

        output += make_table(
            ['Item', 'Mean', 'Std Dev', 'Item-Total Corr.', 'Corrected Item-Total Corr.', 'Alpha if Item Deleted'],
            item_rows, title='Item-Total Statistics'
        )

        # Interpretation
        interp = ''
        if alpha >= 0.9:
            interp = 'Excellent (≥ 0.9)'
        elif alpha >= 0.8:
            interp = 'Good (0.8 – 0.9)'
        elif alpha >= 0.7:
            interp = 'Acceptable (0.7 – 0.8)'
        elif alpha >= 0.6:
            interp = 'Questionable (0.6 – 0.7)'
        elif alpha >= 0.5:
            interp = 'Poor (0.5 – 0.6)'
        else:
            interp = 'Unacceptable (< 0.5)'
        output += make_note(f'Reliability Interpretation: {interp}')
        output += '</div>'
        return output
